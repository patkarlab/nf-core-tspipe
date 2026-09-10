"""Parse the v2 CNV outputs routed into clinical/cnv/ (DASH_CNV_V1).

Layout (ORG_CNV_V1)::

  <sample>/cnv/
    consensus/<sample>.cnv_consensus4.{genes.tsv,segments.tsv,json}
    exon_plots/<sample>.exon_plots.tsv + PNGs
    chrom_pages/<sample>.chrom_pages.tsv + PNGs
    decon/<sample>.decon_filtered.tsv, <sample>.decon.genes.tsv
    purple/<sample>.purple.h_summary.tsv, <sample>.purple.h_genes.tsv, PURPLE files
    sex_check/<sample>.sex_check.tsv

parse() returns a dict merged into ctx["cnv"]:
  consensus_table   {columns, rows, n}   non-neutral, non-blacklisted genes, tier order
  consensus_tiers   {TIER_1: n, ...}
  blacklisted       [gene, ...]
  purple            {status, method, purity, ploidy, gender, trusted}
  sex_check         {column: value} of the sample's row
  decon_table       {columns, rows, n}   reportable calls and multi-exon calls at BF >= 5
  chrom_pages       [{chrom, label, path, n_targets, n_baf_sites, n_depth_bins}]
  exon_plots        [{chrom, reasons, path}]
Standard library only; every element is optional and absent when its file is.
"""

import csv
import re
from pathlib import Path

TIER_ORDER = {"TIER_1": 0, "TIER_2": 1, "REVIEW": 2, "TIER_3": 3}
# MARKER DASH_ANNOT_V1: cytoband beside gene; driver_role, clingen_hi, clingen_ts at the tail
# (CMX_ANNOT_V1 columns; blank on pre-annotation TSVs because rows use r.get(c, ""))
CONSENSUS_COLUMNS = ["gene", "cytoband", "chrom", "start", "end", "consensus_call", "tier", "flags",
                     "k_call", "k_cn", "k_log2", "g_call", "g_seg_log2", "b_call", "p_call", "p_C",
                     "e_call", "e_bf", "h_call", "h_cn_min", "h_cn_max", "h_loh", "loo_fp_any",
                     "driver_role", "clingen_hi", "clingen_ts"]
DECON_COLUMNS = ["Gene", "CNV.type", "N.exons", "Chromosome", "Start", "End", "BF", "Reads.ratio", "decision", "reportable", "exon_flags"]


def _chrom_key(c):
    c = str(c).replace("chr", "").upper()
    if c == "X":
        return (1, 23)
    if c == "Y":
        return (1, 24)
    return (0, int(c)) if c.isdigit() else (2, c)


def _read_tsv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _rel(p, sample_dir):
    try:
        return str(Path(p).relative_to(sample_dir))
    except ValueError:
        return str(p)


def _round(v, nd=2):
    try:
        return "%.*f" % (nd, float(v))
    except (TypeError, ValueError):
        return v


def parse(sample_dir, sample):
    sample_dir = Path(sample_dir)
    v2 = sample_dir / "cnv"
    out = {}
    if not v2.is_dir():
        return out

    # ---- consensus ----
    genes_path = v2 / "consensus" / ("%s.cnv_consensus4.genes.tsv" % sample)
    if genes_path.exists():
        rows = _read_tsv(genes_path)
        tiers, blacklisted, keep = {}, [], []
        for r in rows:
            call = r.get("consensus_call", "")
            if call == "BLACKLISTED":
                blacklisted.append(r.get("gene", ""))
                continue
            if call in ("NEUTRAL", "NA", ""):
                continue
            tiers[r.get("tier", "NA")] = tiers.get(r.get("tier", "NA"), 0) + 1
            for col in ("k_log2", "g_seg_log2", "e_bf", "h_cn_min", "h_cn_max", "loo_fp_any"):
                if col in r:
                    r[col] = _round(r[col], 3 if col == "loo_fp_any" else 2)
            keep.append(dict((c, r.get(c, "")) for c in CONSENSUS_COLUMNS))
        keep.sort(key=lambda r: (TIER_ORDER.get(r["tier"], 9), _chrom_key(r["chrom"]), int(r["start"] or 0)))
        out["consensus_table"] = {"columns": CONSENSUS_COLUMNS, "rows": keep, "n": len(keep)}
        out["consensus_tiers"] = tiers
        out["blacklisted"] = blacklisted

    # ---- PURPLE ----
    ps = v2 / "purple" / ("%s.purple.h_summary.tsv" % sample)
    if ps.exists():
        rows = _read_tsv(ps)
        if rows:
            r = rows[0]
            out["purple"] = {"status": r.get("status", ""), "method": r.get("method", ""), "purity": _round(r.get("purity")),
                             "ploidy": _round(r.get("ploidy")), "gender": r.get("gender", ""), "trusted": r.get("trusted", ""),
                             "comment": r.get("comment", "")}

    # ---- BAF by arm (BAF_V2; BAF_V2B: clinical/cnv/baf/, consensus-JSON fallback, figure) ----
    baf_rows = None
    for cand in (v2 / "baf" / ("%s.baf.summary.tsv" % sample), v2 / ("%s.baf.summary.tsv" % sample)):
        if cand.exists():
            baf_rows = _read_tsv(cand)
            break
    if baf_rows is None:
        cj = v2 / "consensus" / ("%s.cnv_consensus4.json" % sample)
        if cj.exists():
            try:
                import json
                with open(cj) as fh:
                    baf_rows = json.load(fh).get("baf_arms") or None
            except (OSError, ValueError):
                baf_rows = None
    if baf_rows:
        out["baf_arms"] = [{"arm": r.get("arm", ""), "n_het": r.get("n_het", ""), "f": r.get("f_estimate", ""),
                            "cr": r.get("cr_median_log2", ""), "verdict": r.get("verdict", ""),
                            "confidence": r.get("confidence", ""), "scope": r.get("scope", "")} for r in baf_rows]
        out["baf_calls"] = [r for r in out["baf_arms"] if r["verdict"] not in ("NEUTRAL", "INDETERMINATE", "") and r["confidence"] == "HIGH"]
    bp = v2 / "baf" / ("%s.baf.png" % sample)
    if bp.exists():
        out["baf_plot"] = _rel(bp, sample_dir)

    # ---- sex check ----
    sx = v2 / "sex_check" / ("%s.sex_check.tsv" % sample)
    if sx.exists():
        rows = _read_tsv(sx)
        if rows:
            out["sex_check"] = dict((k, _round(v) if k.lower().endswith("ratio") else v) for k, v in rows[-1].items())

    # ---- DECoN ----
    dp = v2 / "decon" / ("%s.decon_filtered.tsv" % sample)
    if dp.exists():
        rows = _read_tsv(dp)
        keep = []
        for r in rows:
            try:
                bf, n_ex = float(r.get("BF", "0")), int(float(r.get("N.exons", "0")))
            except ValueError:
                continue
            if r.get("reportable", "") == "yes" or (n_ex >= 2 and bf >= 5.0):
                r["BF"] = _round(bf, 1); r["Reads.ratio"] = _round(r.get("Reads.ratio"), 2)
                keep.append(dict((c, r.get(c, "")) for c in DECON_COLUMNS))
        keep.sort(key=lambda r: -float(r["BF"] or 0))
        out["decon_table"] = {"columns": DECON_COLUMNS, "rows": keep, "n": len(keep)}

    # ---- chromosome pages ----
    cp = v2 / "chrom_pages" / ("%s.chrom_pages.tsv" % sample)
    if cp.exists():
        pages = []
        for r in _read_tsv(cp):
            f = v2 / "chrom_pages" / r.get("file", "")
            if f.exists():
                pages.append({"chrom": r.get("chroms", r.get("label", "")), "label": r.get("label", ""), "path": _rel(f, sample_dir),
                              "n_targets": r.get("n_targets", ""), "n_baf_sites": r.get("n_baf_sites", ""), "n_depth_bins": r.get("n_depth_bins", "")})
        pages.sort(key=lambda p: _chrom_key(p["chrom"].split(",")[0]))
        out["chrom_pages"] = pages

    # ---- exon plots ----
    ep = v2 / "exon_plots" / ("%s.exon_plots.tsv" % sample)
    if ep.exists():
        plots = []
        for r in _read_tsv(ep):
            f = v2 / "exon_plots" / r.get("file", "")
            if f.exists():
                plots.append({"chrom": r.get("chrom", ""), "reasons": r.get("reasons", ""), "path": _rel(f, sample_dir)})
        plots.sort(key=lambda p: _chrom_key(p["chrom"]))
        out["exon_plots"] = plots
    # ---- genome overview (MARKER VIZ_V1b) and reconCNV (MARKER VIZ_V1) ----
    go = v2 / "chrom_pages" / ("%s.genome.png" % sample)
    if go.exists():
        out["genome_overview"] = _rel(go, sample_dir)
    a17 = v2 / "chrom_pages" / ("%s.17p.png" % sample)   # ARM17P_V1: dedicated 17p figure
    if a17.exists():
        out["arm17p_figure"] = _rel(a17, sample_dir)
    rc = v2 / "reconcnv" / ("%s.reconcnv.html" % sample)
    if rc.exists():
        out["reconcnv"] = _rel(rc, sample_dir)
    return out
