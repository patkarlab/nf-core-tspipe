#!/usr/bin/env python3
"""
patch_cnv_consensus_multi_cmx_v2.py -- consensus arms K/G/B/P/E and a tier
rule; Z-score dropped from support (MARKER CMX_V2). Handoff item 7a.

Edits to bin/cnv_consensus_multi.py (all anchors exact to the 2026-09-06
file; nothing is written unless every anchor matches once):
  1. module docstring rewritten (arms, tier rule, schema v3)
  2. autodetect_zcall() removed; loo_fp_ok() and purecn_cnloh() added
  3. argparse: --decon-genes (optional arm E contract) and --loo-fp-max
  4. legacy passthrough keeps the concordance table but no Z autodetect;
     DECoN table loaded when given
  5. per-gene consensus: depth arms K,G; independent arms B (17p verdict),
     P (trusted PureCN), E (DECoN); consensus_call GAIN/LOSS/CNLOH/
     DISCORDANT/NEUTRAL and tier TIER_1/TIER_2/TIER_3/REVIEW/NA
  6. genes.tsv columns: z_call dropped; b_call, e_call, e_bf, tier added
  7. tracks.cnr_bins carries depth and weight; schema twist_cnv_consensus4/v3
  8. final summary line reports tier counts

Idempotent; dry run by default; --apply writes with a .bak_cmx_v2_<ts> backup.
Nextflow does not hash bin/ scripts, so an existing run needs the consensus
task re-executed by hand or a fresh run to pick this up.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER CMX_V2"
TARGET_DEFAULT = "bin/cnv_consensus_multi.py"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


DOCSTRING = '''"""Multi-arm CNV consensus + Phase-4 JSON payload (CMX_V2).

%s: Z-score is no longer an arm; the legacy concordance table still rides
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
    TIER_3  independent arm(s) only, all agreeing (consensus = direction)
    CNLOH   B and/or P cnLOH support: TIER_1 when both agree, else TIER_2
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
''' % MARKER

HELPERS = '''def loo_fp_ok(value, threshold):
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
    return abs(c - 2.0) < 0.5 and \\
        str(pr.get("p_loh", "")).strip().lower() in ("true", "1", "yes")


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


'''

LEGACY_BLOCK = '''    # ---- legacy concordance passthrough (CMX_V2: Z-score is not an arm)
    lg_header, lg_rows = read_tsv(args.concordance, comment="#")
    gene_col = "gene" if "gene" in lg_header else (
        "Gene" if "Gene" in lg_header else None)
    legacy = {}
    if gene_col is None:
        warn("legacy concordance has no gene/Gene column; passthrough skipped")
    else:
        for r in lg_rows:
            legacy[r[gene_col]] = r

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

'''

PER_GENE_BLOCK = '''    # ---- per-gene consensus (CMX_V2: depth K/G; independent B/P/E; tier rule)
    n_consensus = 0
    tier_counts = {}
    for g in genes:
        k_call, k_cn, k_log2 = cnvkit_gene_call(
            k_segs, g["chrom"], g["start"], g["end"])
        lg = legacy.get(g["gene"], {})
        pr = purecn.get(g["gene"], {})
        p_call = pr.get("p_call", "NA")
        p_cnloh = p_trusted and purecn_cnloh(pr)
        dr = decon.get(g["gene"], {})
        e_call = (norm_call(dr.get("e_call")) or "NA") if dr else "NA"
        e_bf = dr.get("e_bf", "NA") if dr else "NA"
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
                 "E": e_call if e_call in ("GAIN", "LOSS") else None}
        cnloh_arms = [a for a, v in (("B", b_call == "CNLOH"), ("P", p_cnloh)) if v]

        depth_dirs = set(v for v in depth.values() if v)
        indep_dirs = set(v for v in indep.values() if v)
        arms = dict((a, v) for a, v in list(depth.items()) + list(indep.items()) if v)
        for a in cnloh_arms:
            arms.setdefault(a, "CNLOH")
        flags = "".join(sorted(arms))
        fp_ok = loo_fp_ok(loo_fp.get(g["gene"]), args.loo_fp_max)

        if len(depth_dirs) > 1 or (depth_dirs and (indep_dirs - depth_dirs)) \\
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
            tier = "TIER_1" if len(cnloh_arms) >= 2 else "TIER_2"
        elif indep_dirs and len(indep_dirs) == 1 and not cnloh_arms:
            consensus, tier = next(iter(indep_dirs)), "TIER_3"
        elif indep_dirs or cnloh_arms:
            consensus, tier = "DISCORDANT", "REVIEW"
        else:
            consensus, tier = "NEUTRAL", "NA"
        if tier in ("TIER_1", "TIER_2"):
            n_consensus += 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        g.update({
            "k_call": k_call, "k_cn": k_cn, "k_log2": k_log2,
            "b_call": b_call,
            "p_call": p_call, "p_C": pr.get("p_C", "NA"),
            "p_loh": pr.get("p_loh", "NA"),
            "e_call": e_call, "e_bf": e_bf,
            "support": len(arms),
            "flags": flags or "-", "consensus_call": consensus,
            "tier": tier,
            "loo_fp_any": loo_fp.get(g["gene"], "NA"),
            "allelic_state": allelic,
            "legacy": lg,
        })

'''

GENES_TSV_BLOCK = '''    # ---- outputs (CMX_V2 columns)
    gene_cols = [
        "gene", "chrom", "start", "end", "k_call", "k_cn", "k_log2",
        "g_call", "g_seg_log2", "g_n_bins", "b_call",
        "p_call", "p_C", "p_loh", "e_call", "e_bf", "support",
        "flags", "consensus_call", "tier", "loo_fp_any", "allelic_state",
    ]
    with open(args.out_prefix + ".genes.tsv", "w") as out:
        out.write("\\t".join(gene_cols) + "\\n")
        for g in sorted(genes, key=lambda x: (x["chrom"], x["start"])):
            out.write("\\t".join(str(g[c]) for c in gene_cols) + "\\n")

'''

FINAL_PRINT = '''    n_disc = sum(1 for g in genes if g["consensus_call"] == "DISCORDANT")
    print("[ok] {0}: {1} genes, {2} TIER_1/TIER_2 consensus calls, "
          "{3} discordant, {4} intersected segments, baf17p={5}, tiers={6}".format(
              args.sample, len(genes), n_consensus, n_disc,
              len(intersect), baf_verdict,
              ",".join("{0}:{1}".format(k, tier_counts[k]) for k in sorted(tier_counts))))
'''


def patch(t):
    notes = []
    # 1. docstring
    t, n = sub_once(t, r'\A#!/usr/bin/env python3\n"""Four-caller CNV consensus \+ Phase-4 JSON payload \(CMX_V1\)\..*?\n"""\n',
                    lambda m: "#!/usr/bin/env python3\n" + DOCSTRING, "docstring", flags=re.S)
    notes.append(n)
    # 2a. remove autodetect_zcall
    t, n = sub_once(t, r'^def autodetect_zcall\(header\):\n(?:.*\n)*?    return None\n\n\n', "", "remove autodetect_zcall")
    notes.append(n)
    # 2b. helpers before main
    t, n = sub_once(t, r'^def main\(\):\n', lambda m: HELPERS + m.group(0), "helpers before main()")
    notes.append(n)
    # 3. argparse
    t, n = sub_once(t, r'description="Four-caller CNV consensus \(CMX_V1\)"',
                    'description="Multi-arm CNV consensus (CMX_V2)"', "argparse description")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^    ap\.add_argument\("--purecn-summary", default=None,\n                    help="PureCN summary tsv \(PCN_V1\); optional"\)\n',
        lambda m: m.group(0)
        + '    ap.add_argument("--decon-genes", default=None,\n'
        + '                    help="DECoN gene table (gene, e_call, e_bf); optional (CMX_V2 arm E)")\n'
        + '    ap.add_argument("--loo-fp-max", type=float, default=0.10,\n'
        + '                    help="LOO fp_any_rate ceiling for TIER_1/TIER_2 (fraction; default 0.10)")\n',
        "argparse: --decon-genes, --loo-fp-max")
    notes.append(n)
    # 4. legacy block
    t, n = sub_once(t, r'^    # ---- legacy concordance passthrough \+ zscore autodetect\n.*?(?=^    # ---- LOO per-gene fp rate\n)',
                    lambda m: LEGACY_BLOCK, "legacy passthrough block", flags=re.M | re.S)
    notes.append(n)
    # 5. per-gene block
    t, n = sub_once(t, r'^    # ---- per-gene consensus\n.*?(?=^    # ---- segment intersection\n)',
                    lambda m: PER_GENE_BLOCK, "per-gene consensus block", flags=re.M | re.S)
    notes.append(n)
    # 6. genes.tsv writer
    t, n = sub_once(t, r'^    # ---- outputs\n    with open\(args\.out_prefix \+ "\.genes\.tsv", "w"\) as out:\n.*?(?=^    with open\(args\.out_prefix \+ "\.segments\.tsv")',
                    lambda m: GENES_TSV_BLOCK, "genes.tsv writer", flags=re.M | re.S)
    notes.append(n)
    # 7. cnr_bins + schema
    t, n = sub_once(
        t,
        r'^    cnr_bins = \[\[r\["chromosome"\], int\(r\["start"\]\), int\(r\["end"\]\),\n                 r\.get\("gene", ""\), float\(r\["log2"\]\)\] for r in cnr_rows\]\n',
        '    cnr_bins = [[r["chromosome"], int(r["start"]), int(r["end"]),\n'
        '                 r.get("gene", ""), float(r["log2"]),\n'
        '                 safe_float(r.get("depth")), safe_float(r.get("weight"))]\n'
        '                for r in cnr_rows]   # CMX_V2: depth, weight per bin\n',
        "cnr_bins depth/weight")
    notes.append(n)
    t, n = sub_once(t, r'"schema": "twist_cnv_consensus4/v2",', '"schema": "twist_cnv_consensus4/v3",', "schema v3")
    notes.append(n)
    # 8. final print
    t, n = sub_once(t, r'^    n_disc = sum\(1 for g in genes if g\["consensus_call"\] == "DISCORDANT"\)\n.*?len\(intersect\), baf_verdict\)\)\n',
                    lambda m: FINAL_PRINT, "final summary line", flags=re.M | re.S)
    notes.append(n)
    return t, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not os.path.isfile(args.target):
        print("[error] target not found: %s" % args.target)
        sys.exit(1)
    original = open(args.target).read()
    if MARKER in original:
        print("[skip] %s already present" % MARKER)
        sys.exit(0)
    try:
        new_text, notes = patch(original)
    except ValueError as exc:
        print("[error] %s; nothing written" % exc)
        sys.exit(1)
    for n in notes:
        print(n)
    try:
        compile(new_text, args.target, "exec")
    except SyntaxError as exc:
        print("[error] patched file does not compile: %s; nothing written" % exc)
        sys.exit(1)
    leftovers = [w for w in ("z_call", "autodetect_zcall", "z_col") if w in new_text]
    print("[check] marker %d (expected 1); compiles; z-score leftovers: %s"
          % (new_text.count(MARKER), leftovers or "none"))
    if new_text.count(MARKER) != 1 or leftovers:
        print("[error] verification failed; nothing written")
        sys.exit(1)
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cmx_v2_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    print("[backup] %s" % backup)
    with open(args.target, "w") as fh:
        fh.write(new_text)
    print("[patch] wrote %s" % args.target)


if __name__ == "__main__":
    main()
