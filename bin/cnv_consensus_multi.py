#!/usr/bin/env python3
"""Multi-arm CNV consensus + Phase-4 JSON payload (CMX_V2).

MARKER CMX_V2_1 (expected chrX/chrY copy number by --sex)
MARKER CMX_ANNOT_V1 (cytoband, ClinGen HI/TS and hmftools driver-panel role
columns appended to genes.tsv; --cytoband/--clingen/--driver-panel optional)
MARKER CMX_V2: Z-score is no longer an arm; the legacy concordance table still rides
through into the JSON (legacy: {...}) for reference only.

Arms merged at gene level:
  depth (one vote family; K and G are both read depth against the
  sex-stratified PoNs):
    K  CNVkit    -- gene call derived from call.cns integer CN over the
                    gene span (cn > 2 GAIN, cn < 2 LOSS; length-weighted
                    majority when multiple segments overlap).
    G  GATK      -- gene projection table (seg_call +/-/0).
  independent:
    B  BAF       -- sample-level 17p verdict (BAF_V1): genes inside the
                    17p test region get b_call LOSS for DEL_17P, CNLOH for
                    CNLOH_17P; allelic_state carries the verdict text.
    P  PureCN    -- p_call GAIN/LOSS when the fit is trusted (status OK,
                    not flagged); p_C == 2 with p_loh true is cnLOH support.
    E  DECoN     -- optional --decon-genes TSV (gene, e_call, e_bf); the
                    DECON module writes this contract. NA until it exists.

Tier rule (per gene; fp_ok = LOO fp_any_rate < --loo-fp-max, unknown = not ok):
  REVIEW  K and G disagree, or an independent arm contradicts the depth
          direction, or cnLOH evidence coexists with a depth call.
  With a depth direction D from K and/or G:
    TIER_1  >= 1 independent arm agrees with D and fp_ok
    TIER_2  K and G both call D and fp_ok, or an independent arm agrees
            but fp is not ok
    TIER_3  single depth arm, or K and G without fp_ok
  Without a depth call:
    TIER_2  >= 2 independent arms agreeing, no depth arm (CMX_V2_4)
    TIER_3  a single independent arm (consensus = direction)
    CNLOH   TIER_1 with >= 2 allelic arms (B/P/H); TIER_2 from B alone; TIER_3 from P or H alone (CMX_V2_4)
  NEUTRAL otherwise (tier NA).

consensus_call: GAIN | LOSS | CNLOH | DISCORDANT | NEUTRAL.
support: number of non-neutral arms; flags: their letters (e.g. GKP).

Segment intersection: every overlapping (cnvkit segment x GATK called
segment) pair with both values and a concordance flag
(both non-neutral same direction / both neutral -> concordant).

JSON schema v3 (single payload for the three-view report):
{
  "schema": "twist_cnv_consensus4/v3",
  "sample": str, "panel": "twist_myeloid",
  "purecn": {summary row}, "baf17p": {summary row as object},
  "genes": [ {gene, chrom, start, end, k_call, k_cn, k_log2, g_call,
              g_seg_log2, g_n_bins, b_call, p_call, p_C, p_loh, e_call,
              e_bf, support, flags, consensus_call, tier, loo_fp_any,
              allelic_state} ],
  "segments": {"cnvkit": [...], "gatk": [...], "intersect": [...]},
  "tracks":   {"denoised_bins": [[chrom,start,end,log2]...],
               "cnr_bins":      [[chrom,start,end,gene,log2,depth,weight]...],
               "baf_sites":     [[chrom,pos,depth,af_raw,af_adj,het]...]}
}
"""

import argparse
import json
import os
import re
import statistics
import sys

CALL_WORDS = {
    "gain": "GAIN", "amp": "GAIN", "amplification": "GAIN", "dup": "GAIN",
    "loss": "LOSS", "del": "LOSS", "deletion": "LOSS", "hetloss": "LOSS",
    "neutral": "NEUTRAL", "normal": "NEUTRAL", "none": "NEUTRAL", "0": "NEUTRAL",
}


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def warn(msg):
    sys.stderr.write("[warn] {0}\n".format(msg))


def read_tsv(path, sep="\t", comment=None):
    header, rows = None, []
    with open(path) as fh:
        for line in fh:
            if comment and line.startswith(comment):
                continue
            parts = line.rstrip("\n").split(sep)
            if header is None:
                header = parts
                continue
            if len(parts) < len(header):
                continue
            rows.append(dict(zip(header, parts)))
    if header is None:
        fail("empty table: {0}".format(path))
    return header, rows


def read_gatk_table(path, cols):
    header, rows = None, []
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                missing = [c for c in cols if c not in header]
                if missing:
                    fail("{0}: missing {1}".format(path, ",".join(missing)))
                continue
            if len(parts) < len(header):
                continue
            rows.append(dict(zip(header, parts)))
    if not rows:
        fail("no data rows: {0}".format(path))
    return rows


def overlap(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))


def expected_cn(chrom, sex):
    """CMX_V2_1: expected integer copy number of a chromosome for the sample's sex.
    None means not interpretable (X/Y with unknown sex, or chrY in a female)."""
    c = chrom.replace("chr", "")
    if c not in ("X", "Y"):
        return 2
    if sex == "male":
        return 1
    if sex == "female":
        return 2 if c == "X" else None
    return None


def cn_call(cn, exp):
    if cn is None:
        return "NEUTRAL"
    if exp is None:
        return "NA"
    if cn > exp:
        return "GAIN"
    if cn < exp:
        return "LOSS"
    return "NEUTRAL"


def cnvkit_gene_call(segs, chrom, gs, ge, exp=2):
    """Length-weighted call from call.cns integer CN over a gene span,
    relative to the expected copy number `exp` (CMX_V2_1; None -> NA)."""
    w = {"GAIN": 0, "LOSS": 0, "NEUTRAL": 0}
    hits = []
    for s in segs:
        if s["chromosome"] != chrom:
            continue
        o = overlap(gs, ge, s["start"], s["end"])
        if o <= 0:
            continue
        hits.append((o, s))
        call = cn_call(s["cn"], exp)
        w[call if call in w else "NEUTRAL"] += o
    if not hits:
        return "NA", None, None
    if exp is None:
        top = max(hits, key=lambda h: h[0])[1]   # HARDEN_Q6_V1: key on overlap; segment dicts are not orderable (TypeError on ties)
        return "NA", top["cn"], top["log2"]
    call = max(w, key=lambda k: w[k])
    top = max(hits, key=lambda h: h[0])[1]   # HARDEN_Q6_V1: key on overlap; segment dicts are not orderable (TypeError on ties)
    return call, top["cn"], top["log2"]


def norm_call(value):
    if value is None:
        return None
    v = str(value).strip().lower()
    for key, out in CALL_WORDS.items():
        if key in v:
            return out
    return None


def loo_fp_ok(value, threshold):
    """True when the LOO false-positive rate is known and below threshold.
    Accepts a fraction (0.26) or a percent (26.0); NA or unparsable -> False,
    so a gene without a LOO row can never reach TIER_1/TIER_2."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if v > 1.0:
        v = v / 100.0
    return v < threshold


def purecn_cnloh(pr):
    """PureCN gene row implies copy-neutral LOH: integer C of 2 and loh true."""
    try:
        c = float(pr.get("p_C", "NA"))
    except (TypeError, ValueError):
        return False
    return abs(c - 2.0) < 0.5 and \
        str(pr.get("p_loh", "")).strip().lower() in ("true", "1", "yes")


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def strip_chr(chrom):
    """CMX_ANNOT_V1: 'chr17' -> '17'; other names unchanged."""
    c = str(chrom).strip()
    return c[3:] if c.lower().startswith("chr") else c


def read_cytobands(path):
    """CMX_ANNOT_V1: UCSC cytoBand.txt -> {chrom_no_prefix: [(start, end, band)]}."""
    bands = {}
    if not path:
        return bands
    with open(path) as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 4 or f[0].startswith("#"):
                continue
            bands.setdefault(strip_chr(f[0]), []).append((int(f[1]), int(f[2]), f[3]))
    for v in bands.values():
        v.sort()
    return bands


def read_clingen(path):
    """CMX_ANNOT_V1: ClinGen gene curation list -> {gene: (hi_score, ts_score)}.

    The file carries several leading '#' comment lines; the header line
    itself starts with '#Gene Symbol'.
    """
    out = {}
    if not path:
        return out
    hdr = None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if hdr is None:
                if line.startswith("#Gene Symbol") or line.startswith("Gene Symbol"):
                    hdr = line.lstrip("#").split("\t")
                continue
            if not line or line.startswith("#"):
                continue
            r = dict(zip(hdr, line.split("\t")))
            g = r.get("Gene Symbol", "").strip()
            if g:
                out[g] = (r.get("Haploinsufficiency Score", "").strip() or "NA",
                          r.get("Triplosensitivity Score", "").strip() or "NA")
    return out


def read_driver_panel(path):
    """CMX_ANNOT_V1: hmftools DriverGenePanel TSV -> {gene: {column: value}}."""
    out = {}
    if not path:
        return out
    hdr = None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line:
                continue
            f = line.split("\t")
            if hdr is None:
                hdr = f
                continue
            r = dict(zip(hdr, f))
            g = r.get("gene", "").strip()
            if g:
                out[g] = r
    return out


def gene_cytoband(bands, chrom, start, end):
    """CMX_ANNOT_V1: band(s) overlapping [start, end); first-last when several."""
    c = strip_chr(chrom)
    hits = [b for (s, e, b) in bands.get(c, []) if s < end and e > start]
    if not hits:
        return "NA"
    if len(hits) == 1:
        return c + hits[0]
    return "%s%s-%s" % (c, hits[0], hits[-1])


def annotate_gene(g, bands, clingen, drivers):
    """CMX_ANNOT_V1: annotation columns for one consensus gene row."""
    hi, ts = clingen.get(g["gene"], ("NA", "NA"))
    d = drivers.get(g["gene"], {})

    def tf(key):
        v = str(d.get(key, "")).strip().upper()
        return v if v in ("TRUE", "FALSE") else "NA"

    role = (d.get("likelihoodType") or "").strip() if d else ""
    amp = tf("reportAmplification")
    ratio = (d.get("amplificationRatio") or "").strip() if (d and amp == "TRUE") else ""
    return {
        "cytoband": gene_cytoband(bands, g["chrom"], int(g["start"]), int(g["end"])),
        "clingen_hi": hi,
        "clingen_ts": ts,
        "driver_role": role or "NA",
        "driver_report_del": tf("reportDeletion"),
        "driver_report_amp": amp,
        "driver_amp_ratio": ratio or "NA",
    }


def read_gene_blacklist(path):
    """CNV_BLACKLIST_V1: gene symbols from a TSV with a 'gene' column (or first column); empty if no file."""
    genes = set()
    if not path or not os.path.isfile(path):
        return genes
    with open(path) as fh:
        header = None
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                if "gene" in header:
                    continue
                genes.add(parts[0].strip())
                continue
            idx = header.index("gene") if "gene" in header else 0
            if len(parts) > idx and parts[idx].strip():
                genes.add(parts[idx].strip())
    return genes


def main():
    ap = argparse.ArgumentParser(description="Multi-arm CNV consensus (CMX_V2)")
    for name in ["sample", "cnr", "call-cns", "gatk-genes",
                 "gatk-called", "denoised", "baf-summary", "baf-sites",
                 "loo-summary", "out-prefix"]:
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--concordance", default=None,
                    help="legacy two-caller concordance table; accepted and ignored (CNV_RETIRE_7B)")
    ap.add_argument("--purecn-genes", default=None,
                    help="PureCN normalised gene table (PCN_V1); optional")
    ap.add_argument("--purecn-summary", default=None,
                    help="PureCN summary tsv (PCN_V1); optional")
    ap.add_argument("--decon-genes", default=None,
                    help="DECoN gene table (gene, e_call, e_bf); optional (CMX_V2 arm E)")
    ap.add_argument("--loo-fp-max", type=float, default=0.10,
                    help="LOO fp_any_rate ceiling for TIER_1/TIER_2 (fraction; default 0.10)")
    ap.add_argument("--sex", default="unknown",
                    help="sample sex (male|female|unknown) for the expected chrX/chrY copy number (CMX_V2_1)")
    ap.add_argument("--gene-blacklist", default=None,
                    help="TSV of genes never called (consensus BLACKLISTED); optional (CNV_BLACKLIST_V1)")
    ap.add_argument("--purple-genes", default=None, help="PURPLE arm H gene table (HMF_PURPLE_V1); optional")
    ap.add_argument("--purple-summary", default=None, help="PURPLE arm H summary (HMF_PURPLE_V1); optional")
    ap.add_argument("--cytoband", default=None, help="UCSC cytoBand.txt (CMX_ANNOT_V1); optional")
    ap.add_argument("--clingen", default=None, help="ClinGen gene curation list, GRCh38 (CMX_ANNOT_V1); optional")
    ap.add_argument("--driver-panel", default=None, help="hmftools DriverGenePanel TSV (CMX_ANNOT_V1); optional")
    args = ap.parse_args()

    for p in [args.cnr, args.call_cns, args.gatk_genes,
              args.gatk_called, args.denoised, args.baf_summary,
              args.baf_sites, args.loo_summary]:
        if not os.path.isfile(p):
            fail("input not found: {0}".format(p))

    # ---- CNVkit segments (call.cns: chromosome start end gene log2 ... cn)
    cns_header, cns_rows = read_tsv(args.call_cns)
    for need in ("chromosome", "start", "end", "log2"):
        if need not in cns_header:
            fail("call.cns missing column {0}".format(need))
    k_segs = []
    for r in cns_rows:
        cn = r.get("cn")
        k_segs.append({
            "chromosome": r["chromosome"], "start": int(r["start"]),
            "end": int(r["end"]), "log2": float(r["log2"]),
            "cn": int(cn) if cn not in (None, "", "NA") else None,
        })

    # ---- GATK gene projection + called segments
    g_rows = read_gatk_table(args.gatk_genes, ["gene", "chrom", "start", "end"]) \
        if open(args.gatk_genes).readline().startswith("gene") \
        else None
    if g_rows is None:
        fail("gatk genes table has unexpected header")
    g_by_gene = dict((r["gene"], r) for r in g_rows)

    g_segs = []
    for r in read_gatk_table(args.gatk_called,
                             ["CONTIG", "START", "END",
                              "MEAN_LOG2_COPY_RATIO", "CALL"]):
        g_segs.append({
            "chromosome": r["CONTIG"], "start": int(r["START"]),
            "end": int(r["END"]), "log2": float(r["MEAN_LOG2_COPY_RATIO"]),
            "call": {"+": "GAIN", "-": "LOSS"}.get(r["CALL"], "NEUTRAL"),
        })

    # ---- gene universe from the GATK projection (exonwise-derived)
    genes = []
    for r in g_rows:
        genes.append({
            "gene": r["gene"], "chrom": r["chrom"],
            "start": int(r["start"]), "end": int(r["end"]),
            "g_call": {"+": "GAIN", "-": "LOSS", "0": "NEUTRAL"}.get(
                r.get("seg_call", "NA"), "NA"),
            "g_seg_log2": r.get("seg_mean_log2", "NA"),
            "g_n_bins": r.get("n_bins", "NA"),
        })

    # ---- legacy concordance passthrough retired (CNV_RETIRE_7B); --concordance is ignored
    legacy = {}

    # ---- DECoN exon-level arm E (CMX_V2; optional until the DECON module exists)
    # Contract: TSV with columns gene, e_call (GAIN|LOSS|NEUTRAL), e_bf.
    decon = {}
    if args.decon_genes:
        if not os.path.isfile(args.decon_genes):
            warn("--decon-genes not found: {0}; E support omitted".format(args.decon_genes))
        else:
            d_hdr, d_rows = read_tsv(args.decon_genes, comment="#")
            if "gene" in d_hdr and "e_call" in d_hdr:
                for r in d_rows:
                    decon[r["gene"]] = r
                print("[ok] DECoN gene table: {0} rows".format(len(decon)))
            else:
                warn("--decon-genes lacks gene/e_call columns; E support omitted")

    # ---- MARKER CNV_BLACKLIST_V1: panel gene blacklist
    blacklist = read_gene_blacklist(args.gene_blacklist)
    cytobands = read_cytobands(args.cytoband)   # CMX_ANNOT_V1
    clingen = read_clingen(args.clingen)   # CMX_ANNOT_V1
    drivers = read_driver_panel(args.driver_panel)   # CMX_ANNOT_V1
    if blacklist:
        print("[ok] gene blacklist: {0} gene(s)".format(len(blacklist)))

    # ---- LOO per-gene fp rate
    loo_fp = {}
    for r in read_tsv(args.loo_summary)[1]:
        if "gene" in r and "fp_any_rate" in r:
            loo_fp[r["gene"]] = r["fp_any_rate"]

    # ---- BAF summary
    baf_hdr, baf_rows = read_tsv(args.baf_summary, comment="#")
    baf = baf_rows[0] if baf_rows else {}
    baf_region = baf.get("region", "chr17:0-0")
    m = re.match(r"(chr\w+):(\d+)-(\d+)", baf_region)
    baf_chrom, baf_lo, baf_hi = (m.group(1), int(m.group(2)), int(m.group(3))) \
        if m else ("chr17", 0, 0)
    baf_verdict = baf.get("verdict", "NA")

    # ---- PureCN (PCN_V1; optional, FAILED-tolerant)
    purecn = {}
    purecn_sum = {"status": "ABSENT"}
    if args.purecn_summary and os.path.isfile(args.purecn_summary):
        ps_rows = read_tsv(args.purecn_summary)[1]
        if ps_rows:
            purecn_sum = ps_rows[0]
    # MARKER: purecn_flagged_degrade
    # A flagged fit (poor GOF, noisy log-ratio, dropout) keeps its calls in
    # the table as advisory but contributes no consensus support.
    p_trusted = False
    if args.purecn_genes and os.path.isfile(args.purecn_genes) \
            and purecn_sum.get("status") == "OK":
        for r in read_tsv(args.purecn_genes)[1]:
            purecn[r["gene"]] = r
        if str(purecn_sum.get("flagged", "")).strip().upper() == "TRUE":
            warn("PureCN flagged=TRUE ({0}); P calls retained as advisory, "
                 "P support omitted".format(purecn_sum.get("comment", "")))
        else:
            p_trusted = True
    elif args.purecn_genes:
        warn("PureCN status={0}; P support omitted".format(
            purecn_sum.get("status")))

    # ---- MARKER HMF_PURPLE_V1: PURPLE (hmftools) arm H; optional; FAIL_ status -> advisory
    purple_h = {}
    purple_h_sum = {"status": "ABSENT"}
    h_trusted = False
    if args.purple_summary and os.path.isfile(args.purple_summary):
        hs_rows = read_tsv(args.purple_summary)[1]
        if hs_rows:
            purple_h_sum = hs_rows[0]
    if args.purple_genes and os.path.isfile(args.purple_genes):
        for r in read_tsv(args.purple_genes)[1]:
            purple_h[r["gene"]] = r
        h_trusted = str(purple_h_sum.get("trusted", "")).strip().upper() == "TRUE" \
            and "WARN_LOW_PURITY" not in str(purple_h_sum.get("status", ""))   # MARKER CMX_V2_4
        if not h_trusted:
            warn("PURPLE status={0}; H calls retained as advisory, H support omitted".format(purple_h_sum.get("status")))
        else:
            print("[ok] PURPLE arm H: status={0} purity={1} ploidy={2}".format(
                purple_h_sum.get("status"), purple_h_sum.get("purity"), purple_h_sum.get("ploidy")))

    # ---- per-gene consensus (CMX_V2: depth K/G; independent B/P/E; tier rule)
    n_consensus = 0
    tier_counts = {}
    for g in genes:
        k_call, k_cn, k_log2 = cnvkit_gene_call(
            k_segs, g["chrom"], g["start"], g["end"],
            expected_cn(g["chrom"], args.sex))   # CMX_V2_1
        lg = legacy.get(g["gene"], {})
        pr = purecn.get(g["gene"], {})
        p_call = pr.get("p_call", "NA")
        p_cnloh = p_trusted and purecn_cnloh(pr)
        dr = decon.get(g["gene"], {})
        e_call = (norm_call(dr.get("e_call")) or "NA") if dr else "NA"
        e_bf = dr.get("e_bf", "NA") if dr else "NA"
        hr = purple_h.get(g["gene"], {})
        h_call = hr.get("h_call", "NA")
        h_loh = str(hr.get("h_loh", "")).strip().upper() == "TRUE"
        h_cnloh = h_trusted and h_loh and h_call == "NEUTRAL"
        in_baf_region = g["chrom"] == baf_chrom and overlap(
            g["start"], g["end"], baf_lo, baf_hi) > 0
        b_call = "NA"
        if in_baf_region:
            b_call = {"DEL_17P": "LOSS", "CNLOH_17P": "CNLOH",
                      "NEUTRAL": "NEUTRAL"}.get(baf_verdict, "NA")
        allelic = baf_verdict if in_baf_region else "NA"

        depth = {"K": k_call if k_call in ("GAIN", "LOSS") else None,
                 "G": g["g_call"] if g["g_call"] in ("GAIN", "LOSS") else None}
        indep = {"B": b_call if b_call in ("GAIN", "LOSS") else None,
                 "P": p_call if (p_trusted and p_call in ("GAIN", "LOSS")) else None,
                 "E": e_call if e_call in ("GAIN", "LOSS") else None,
                 "H": h_call if (h_trusted and h_call in ("GAIN", "LOSS")) else None}
        cnloh_arms = [a for a, v in (("B", b_call == "CNLOH"), ("P", p_cnloh), ("H", h_cnloh)) if v]

        depth_dirs = set(v for v in depth.values() if v)
        indep_dirs = set(v for v in indep.values() if v)
        arms = dict((a, v) for a, v in list(depth.items()) + list(indep.items()) if v)
        for a in cnloh_arms:
            arms.setdefault(a, "CNLOH")
        flags = "".join(sorted(arms))
        fp_ok = loo_fp_ok(loo_fp.get(g["gene"]), args.loo_fp_max)

        if len(depth_dirs) > 1 or (depth_dirs and (indep_dirs - depth_dirs)) \
                or (depth_dirs and cnloh_arms):
            consensus, tier = "DISCORDANT", "REVIEW"
        elif depth_dirs:
            consensus = next(iter(depth_dirs))
            n_depth = sum(1 for v in depth.values() if v)
            n_indep = sum(1 for v in indep.values() if v == consensus)
            if n_indep >= 1 and fp_ok:
                tier = "TIER_1"
            elif (n_depth == 2 and fp_ok) or n_indep >= 1:
                tier = "TIER_2"
            else:
                tier = "TIER_3"
        elif cnloh_arms and not indep_dirs:
            consensus = "CNLOH"
            # CMX_V2_4: single-arm cnLOH is TIER_2 only from B (direct BAF); P/H alone TIER_3
            tier = "TIER_1" if len(cnloh_arms) >= 2 else ("TIER_2" if cnloh_arms == ["B"] else "TIER_3")
        elif indep_dirs and len(indep_dirs) == 1 and not cnloh_arms:
            consensus = next(iter(indep_dirs))
            # CMX_V2_4: >= 2 independent arms agreeing without depth -> TIER_2
            tier = "TIER_2" if sum(1 for v in indep.values() if v == consensus) >= 2 else "TIER_3"
        elif indep_dirs or cnloh_arms:
            consensus, tier = "DISCORDANT", "REVIEW"
        else:
            consensus, tier = "NEUTRAL", "NA"
        if g["gene"] in blacklist:   # CNV_BLACKLIST_V1: arms kept for audit, no call
            consensus, tier = "BLACKLISTED", "NA"
            arms, flags = {}, ""
        if tier in ("TIER_1", "TIER_2"):
            n_consensus += 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        g.update({
            "k_call": k_call, "k_cn": k_cn, "k_log2": k_log2,
            "b_call": b_call,
            "p_call": p_call, "p_C": pr.get("p_C", "NA"),
            "p_loh": pr.get("p_loh", "NA"),
            "e_call": e_call, "e_bf": e_bf,
            "h_call": h_call, "h_cn_min": hr.get("h_cn_min", "NA"),
            "h_cn_max": hr.get("h_cn_max", "NA"), "h_macn_min": hr.get("h_macn_min", "NA"),
            "h_loh": "TRUE" if h_loh else ("FALSE" if hr else "NA"),
            "support": len(arms),
            "flags": flags or "-", "consensus_call": consensus,
            "tier": tier,
            "loo_fp_any": loo_fp.get(g["gene"], "NA"),
            "allelic_state": allelic,
            "legacy": lg,
        })
        g.update(annotate_gene(g, cytobands, clingen, drivers))   # CMX_ANNOT_V1

    # ---- segment intersection
    intersect = []
    for ks in k_segs:
        k_call = cn_call(ks["cn"], expected_cn(ks["chromosome"], args.sex))   # CMX_V2_1
        for gs in g_segs:
            if gs["chromosome"] != ks["chromosome"]:
                continue
            o = overlap(ks["start"], ks["end"], gs["start"], gs["end"])
            if o <= 0:
                continue
            intersect.append({
                "chromosome": ks["chromosome"],
                "start": max(ks["start"], gs["start"]),
                "end": min(ks["end"], gs["end"]),
                "cnvkit_log2": ks["log2"], "cnvkit_cn": ks["cn"],
                "cnvkit_call": k_call,
                "gatk_log2": gs["log2"], "gatk_call": gs["call"],
                "concordant": k_call == gs["call"],
            })

    # ---- outputs (CMX_V2 columns)
    gene_cols = [
        "gene", "chrom", "start", "end", "k_call", "k_cn", "k_log2",
        "g_call", "g_seg_log2", "g_n_bins", "b_call",
        "p_call", "p_C", "p_loh", "e_call", "e_bf",
        "h_call", "h_cn_min", "h_cn_max", "h_macn_min", "h_loh", "support",
        "flags", "consensus_call", "tier", "loo_fp_any", "allelic_state",
        "cytoband", "clingen_hi", "clingen_ts",   # CMX_ANNOT_V1
        "driver_role", "driver_report_del", "driver_report_amp", "driver_amp_ratio",
    ]
    with open(args.out_prefix + ".genes.tsv", "w") as out:
        out.write("\t".join(gene_cols) + "\n")
        for g in sorted(genes, key=lambda x: (x["chrom"], x["start"])):
            out.write("\t".join(str(g[c]) for c in gene_cols) + "\n")

    with open(args.out_prefix + ".segments.tsv", "w") as out:
        out.write("chromosome\tstart\tend\tcnvkit_log2\tcnvkit_cn\t"
                  "cnvkit_call\tgatk_log2\tgatk_call\tconcordant\n")
        for s in intersect:
            out.write("\t".join(str(s[c]) for c in [
                "chromosome", "start", "end", "cnvkit_log2", "cnvkit_cn",
                "cnvkit_call", "gatk_log2", "gatk_call", "concordant",
            ]) + "\n")

    den_bins = [[r["CONTIG"], int(r["START"]), int(r["END"]),
                 float(r["LOG2_COPY_RATIO"])]
                for r in read_gatk_table(
                    args.denoised, ["CONTIG", "START", "END",
                                    "LOG2_COPY_RATIO"])]
    cnr_hdr, cnr_rows = read_tsv(args.cnr)
    cnr_bins = [[r["chromosome"], int(r["start"]), int(r["end"]),
                 r.get("gene", ""), float(r["log2"]),
                 safe_float(r.get("depth")), safe_float(r.get("weight"))]
                for r in cnr_rows]   # CMX_V2: depth, weight per bin
    site_hdr, site_rows = read_tsv(args.baf_sites)
    baf_sites = [[r["contig"], int(r["position"]), int(r["depth"]),
                  float(r["af_raw"]), float(r["af_adj"]),
                  r["sample_het"] == "true"] for r in site_rows]

    payload = {
        "schema": "twist_cnv_consensus4/v4",
        "purecn": purecn_sum,
        "purple": purple_h_sum,
        "sample": args.sample,
        "panel": "twist_myeloid",
        "baf17p": baf,
        "genes": [dict((k, v) for k, v in g.items() if k != "legacy")
                  for g in genes],
        "segments": {
            "cnvkit": k_segs,
            "gatk": g_segs,
            "intersect": intersect,
        },
        "tracks": {
            "denoised_bins": den_bins,
            "cnr_bins": cnr_bins,
            "baf_sites": baf_sites,
        },
    }
    with open(args.out_prefix + ".json", "w") as out:
        json.dump(payload, out)

    n_disc = sum(1 for g in genes if g["consensus_call"] == "DISCORDANT")
    print("[ok] {0}: {1} genes, {2} TIER_1/TIER_2 consensus calls, "
          "{3} discordant, {4} intersected segments, baf17p={5}, tiers={6}".format(
              args.sample, len(genes), n_consensus, n_disc,
              len(intersect), baf_verdict,
              ",".join("{0}:{1}".format(k, tier_counts[k]) for k in sorted(tier_counts))))


if __name__ == "__main__":
    main()
