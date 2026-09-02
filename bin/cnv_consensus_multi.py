#!/usr/bin/env python3
"""Four-caller CNV consensus + Phase-4 JSON payload (CMX_V1).

Callers merged at gene level:
  K  CNVkit    -- gene call derived from call.cns integer CN over the
                  gene span (cn > 2 GAIN, cn < 2 LOSS; length-weighted
                  majority when multiple segments overlap).
  Z  Z-score   -- the sample's zscore gene table is NOT re-derived; its
                  columns ride through from the legacy concordance table
                  (prefixed legacy_), and a call column is autodetected
                  (name matching call/status/direction with values
                  gain/loss/amp/del/neutral). If autodetect fails, Z
                  support is omitted with a loud [warn].
  G  GATK      -- gene projection table (seg_call +/-/0).
  B  BAF       -- sample-level 17p verdict; genes inside the 17p test
                  region additionally carry allelic_state.

consensus_call: GAIN/LOSS when >= 2 depth callers (K/Z/G) agree on
direction; single-caller non-neutral -> SINGLE_<dir>(<flags>);
conflicting directions -> DISCORDANT; else NEUTRAL. LOO fp_any_rate is
annotated per gene where the LOO summary carries a gene row.

Segment intersection: every overlapping (cnvkit segment x GATK called
segment) pair with both values and a concordance flag
(both non-neutral same direction / both neutral -> concordant).

JSON schema v1 (single payload for the three-view report):
{
  "schema": "twist_cnv_consensus4/v1",
  "sample": str, "panel": "twist_myeloid",
  "baf17p": {summary row as object},
  "genes": [ {gene, chrom, start, end, k_call, k_cn, k_log2, z_call,
              g_call, g_seg_log2, g_n_bins, support, flags,
              consensus_call, loo_fp_any, allelic_state, legacy: {...}} ],
  "segments": {"cnvkit": [...], "gatk": [...], "intersect": [...]},
  "tracks":   {"denoised_bins": [[chrom,start,end,log2]...],
               "cnr_bins":      [[chrom,start,end,gene,log2]...],
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


def cnvkit_gene_call(segs, chrom, gs, ge):
    """Length-weighted call from call.cns integer CN over a gene span."""
    w = {"GAIN": 0, "LOSS": 0, "NEUTRAL": 0}
    hits = []
    for s in segs:
        if s["chromosome"] != chrom:
            continue
        o = overlap(gs, ge, s["start"], s["end"])
        if o <= 0:
            continue
        hits.append((o, s))
        if s["cn"] is None:
            w["NEUTRAL"] += o
        elif s["cn"] > 2:
            w["GAIN"] += o
        elif s["cn"] < 2:
            w["LOSS"] += o
        else:
            w["NEUTRAL"] += o
    if not hits:
        return "NA", None, None
    call = max(w, key=lambda k: w[k])
    top = max(hits)[1]
    return call, top["cn"], top["log2"]


def autodetect_zcall(header):
    for col in header:
        if re.search(r"call|status|direction", col, re.IGNORECASE):
            return col
    return None


def norm_call(value):
    if value is None:
        return None
    v = str(value).strip().lower()
    for key, out in CALL_WORDS.items():
        if key in v:
            return out
    return None


def main():
    ap = argparse.ArgumentParser(description="Four-caller CNV consensus (CMX_V1)")
    for name in ["sample", "concordance", "cnr", "call-cns", "gatk-genes",
                 "gatk-called", "denoised", "baf-summary", "baf-sites",
                 "loo-summary", "out-prefix"]:
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--purecn-genes", default=None,
                    help="PureCN normalised gene table (PCN_V1); optional")
    ap.add_argument("--purecn-summary", default=None,
                    help="PureCN summary tsv (PCN_V1); optional")
    args = ap.parse_args()

    for p in [args.concordance, args.cnr, args.call_cns, args.gatk_genes,
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

    # ---- legacy concordance passthrough + zscore autodetect
    lg_header, lg_rows = read_tsv(args.concordance, comment="#")
    gene_col = "gene" if "gene" in lg_header else (
        "Gene" if "Gene" in lg_header else None)
    legacy = {}
    z_col = autodetect_zcall([c for c in lg_header if c != gene_col]) \
        if gene_col else None
    if gene_col is None:
        warn("legacy concordance has no gene/Gene column; passthrough skipped")
    else:
        for r in lg_rows:
            legacy[r[gene_col]] = r
        if z_col:
            print("[ok] zscore call column autodetected: {0}".format(z_col))
        else:
            warn("no zscore call column detected; Z support omitted")

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

    # ---- per-gene consensus
    n_consensus = 0
    for g in genes:
        k_call, k_cn, k_log2 = cnvkit_gene_call(
            k_segs, g["chrom"], g["start"], g["end"])
        z_call = None
        lg = legacy.get(g["gene"], {})
        if z_col and lg:
            z_call = norm_call(lg.get(z_col))
        pr = purecn.get(g["gene"], {})
        p_call = pr.get("p_call", "NA")
        calls = {"K": k_call if k_call in ("GAIN", "LOSS") else None,
                 "Z": z_call if z_call in ("GAIN", "LOSS") else None,
                 "G": g["g_call"] if g["g_call"] in ("GAIN", "LOSS") else None,
                 "P": p_call if (p_trusted and p_call in ("GAIN", "LOSS")) else None}
        nonneutral = dict((k, v) for k, v in calls.items() if v)
        dirs = set(nonneutral.values())
        flags = "".join(sorted(nonneutral))
        if len(nonneutral) >= 2 and len(dirs) == 1:
            consensus = dirs.pop()
            n_consensus += 1
        elif len(dirs) > 1:
            consensus = "DISCORDANT"
        elif len(nonneutral) == 1:
            consensus = "SINGLE_{0}({1})".format(list(dirs)[0], flags)
        else:
            consensus = "NEUTRAL"
        allelic = "NA"
        if g["chrom"] == baf_chrom and overlap(
                g["start"], g["end"], baf_lo, baf_hi) > 0:
            allelic = baf_verdict
        g.update({
            "k_call": k_call, "k_cn": k_cn, "k_log2": k_log2,
            "z_call": z_call or "NA",
            "p_call": p_call, "p_C": pr.get("p_C", "NA"),
            "p_loh": pr.get("p_loh", "NA"),
            "support": len(nonneutral),
            "flags": flags or "-", "consensus_call": consensus,
            "loo_fp_any": loo_fp.get(g["gene"], "NA"),
            "allelic_state": allelic,
            "legacy": lg,
        })

    # ---- segment intersection
    intersect = []
    for ks in k_segs:
        k_call = "NEUTRAL" if ks["cn"] in (None, 2) else (
            "GAIN" if ks["cn"] > 2 else "LOSS")
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

    # ---- outputs
    with open(args.out_prefix + ".genes.tsv", "w") as out:
        out.write("gene\tchrom\tstart\tend\tk_call\tk_cn\tk_log2\tz_call\t"
                  "g_call\tg_seg_log2\tg_n_bins\tp_call\tp_C\tp_loh\t"
                  "support\tflags\tconsensus_call\tloo_fp_any\tallelic_state\n")
        for g in sorted(genes, key=lambda x: (x["chrom"], x["start"])):
            out.write("\t".join(str(g[c]) for c in [
                "gene", "chrom", "start", "end", "k_call", "k_cn", "k_log2",
                "z_call", "g_call", "g_seg_log2", "g_n_bins",
                "p_call", "p_C", "p_loh", "support",
                "flags", "consensus_call", "loo_fp_any", "allelic_state",
            ]) + "\n")

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
                 r.get("gene", ""), float(r["log2"])] for r in cnr_rows]
    site_hdr, site_rows = read_tsv(args.baf_sites)
    baf_sites = [[r["contig"], int(r["position"]), int(r["depth"]),
                  float(r["af_raw"]), float(r["af_adj"]),
                  r["sample_het"] == "true"] for r in site_rows]

    payload = {
        "schema": "twist_cnv_consensus4/v2",
        "purecn": purecn_sum,
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
    print("[ok] {0}: {1} genes, {2} multi-caller consensus calls, "
          "{3} discordant, {4} intersected segments, baf17p={5}".format(
              args.sample, len(genes), n_consensus, n_disc,
              len(intersect), baf_verdict))


if __name__ == "__main__":
    main()
