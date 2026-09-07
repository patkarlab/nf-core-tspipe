#!/usr/bin/env python3
"""tools/patches/<date>/patch_cmx_annot_v1.py -- MARKER CMX_ANNOT_V1

C1 (register 2026-09-07): CNV_ANNOTATE replacement inside the consensus.
Appends seven columns to <sample>.cnv_consensus4.genes.tsv (and the same
keys to the JSON genes[] rows); no existing column is renamed or moved:

    cytoband           UCSC band(s) overlapping the gene span, e.g. 17p13.1,
                       or first-last when a gene straddles bands (7q22.1-q22.3)
    clingen_hi         ClinGen Haploinsufficiency Score (raw), NA if absent
    clingen_ts         ClinGen Triplosensitivity Score (raw), NA if absent
    driver_role        hmftools DriverGenePanel likelihoodType (ONCO/TSG)
    driver_report_del  reportDeletion (TRUE/FALSE)
    driver_report_amp  reportAmplification (TRUE/FALSE)
    driver_amp_ratio   amplificationRatio, only when reportAmplification is TRUE

Assets are optional at every level: missing file -> empty input -> column NA.
Decisions (Nikhil, 2026-09-08): role from hmftools DriverGenePanel, full band.

Files touched:
    bin/cnv_consensus_multi.py        loaders, --cytoband/--clingen/--driver-panel,
                                      per-gene annotation, gene_cols extension
    modules/local/cnv_consensus_multi.nf   three path inputs, annot_arg, cache-bust comment
    workflows/tspipe.nf               asset resolution (params override, assets fallback)
                                      and the CNV_CONSENSUS_MULTI call

Usage:  python3 tools/patches/<date>/patch_cmx_annot_v1.py            # dry run
        python3 tools/patches/<date>/patch_cmx_annot_v1.py --apply
Guard:  MARKER CMX_ANNOT_V1 present in a file -> that file is reported as
        already patched and skipped. Every anchor must match exactly once in
        every remaining file before anything is written (all-or-nothing).
        Backups: <file>.bak_cmx_annot_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "CMX_ANNOT_V1"
TAG = "cmx_annot_v1"
REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# bin/cnv_consensus_multi.py
# ---------------------------------------------------------------------------

PY = "bin/cnv_consensus_multi.py"

PY_DOC_OLD = "MARKER CMX_V2_1 (expected chrX/chrY copy number by --sex)\n"
PY_DOC_NEW = (
    "MARKER CMX_V2_1 (expected chrX/chrY copy number by --sex)\n"
    "MARKER CMX_ANNOT_V1 (cytoband, ClinGen HI/TS and hmftools driver-panel role\n"
    "columns appended to genes.tsv; --cytoband/--clingen/--driver-panel optional)\n"
)

PY_LOADERS_ANCHOR = "def read_gene_blacklist(path):\n"
PY_LOADERS_NEW = '''def strip_chr(chrom):
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
            f = line.rstrip("\\n").split("\\t")
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
            line = line.rstrip("\\r\\n")
            if hdr is None:
                if line.startswith("#Gene Symbol") or line.startswith("Gene Symbol"):
                    hdr = line.lstrip("#").split("\\t")
                continue
            if not line or line.startswith("#"):
                continue
            r = dict(zip(hdr, line.split("\\t")))
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
            line = line.rstrip("\\r\\n")
            if not line:
                continue
            f = line.split("\\t")
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


'''

PY_ARGS_OLD = (
    '    ap.add_argument("--purple-summary", default=None, '
    'help="PURPLE arm H summary (HMF_PURPLE_V1); optional")\n'
)
PY_ARGS_NEW = PY_ARGS_OLD + (
    '    ap.add_argument("--cytoband", default=None, help="UCSC cytoBand.txt (CMX_ANNOT_V1); optional")\n'
    '    ap.add_argument("--clingen", default=None, help="ClinGen gene curation list, GRCh38 (CMX_ANNOT_V1); optional")\n'
    '    ap.add_argument("--driver-panel", default=None, help="hmftools DriverGenePanel TSV (CMX_ANNOT_V1); optional")\n'
)

# Loading is anchored on the blacklist read so it happens once, before the gene loop.
PY_LOAD_ANCHOR = "read_gene_blacklist(args.gene_blacklist)"
PY_LOAD_NEW = (
    "    cytobands = read_cytobands(args.cytoband)   # CMX_ANNOT_V1\n"
    "    clingen = read_clingen(args.clingen)   # CMX_ANNOT_V1\n"
    "    drivers = read_driver_panel(args.driver_panel)   # CMX_ANNOT_V1\n"
)

PY_ANNOT_OLD = (
    '            "allelic_state": allelic,\n'
    '            "legacy": lg,\n'
    '        })\n'
)
PY_ANNOT_NEW = PY_ANNOT_OLD + (
    "        g.update(annotate_gene(g, cytobands, clingen, drivers))   # CMX_ANNOT_V1\n"
)

PY_COLS_OLD = (
    '        "flags", "consensus_call", "tier", "loo_fp_any", "allelic_state",\n'
    '    ]\n'
)
PY_COLS_NEW = (
    '        "flags", "consensus_call", "tier", "loo_fp_any", "allelic_state",\n'
    '        "cytoband", "clingen_hi", "clingen_ts",   # CMX_ANNOT_V1\n'
    '        "driver_role", "driver_report_del", "driver_report_amp", "driver_amp_ratio",\n'
    '    ]\n'
)

# ---------------------------------------------------------------------------
# modules/local/cnv_consensus_multi.nf
# ---------------------------------------------------------------------------

NF = "modules/local/cnv_consensus_multi.nf"

NF_HDR_OLD = "MARKER CMX_V2_1: --sex)"
NF_HDR_NEW = "MARKER CMX_V2_1: --sex; MARKER CMX_ANNOT_V1: cytoband/ClinGen/driver-panel annotation)"

NF_IN_OLD = (
    "        path gene_blacklist   // MARKER CNV_BLACKLIST_V1 (empty list when the panel has none)\n"
)
NF_IN_NEW = NF_IN_OLD + (
    "        path cytoband         // MARKER CMX_ANNOT_V1 (empty list when absent)\n"
    "        path clingen          // MARKER CMX_ANNOT_V1 (empty list when absent)\n"
    "        path driver_panel     // MARKER CMX_ANNOT_V1 (empty list when absent)\n"
)

NF_DEF_OLD = (
    '        def purple_arg = (purple_genes && purple_summary) ? '
    '"--purple-genes ${purple_genes} --purple-summary ${purple_summary}" : \'\'   // HMF_PURPLE_V1\n'
)
NF_DEF_NEW = NF_DEF_OLD + (
    "        def annot_arg = [\n"
    "            cytoband     ? \"--cytoband ${cytoband}\"         : '',\n"
    "            clingen      ? \"--clingen ${clingen}\"           : '',\n"
    "            driver_panel ? \"--driver-panel ${driver_panel}\" : '',\n"
    "        ].findAll().join(' ')   // CMX_ANNOT_V1\n"
)

NF_CACHE_OLD = (
    "        # consensus rule version: CMX_V2_4; inputs CNV_RETIRE_7B "
    "(bash comment; busts the task cache)\n"
)
NF_CACHE_NEW = (
    "        # consensus rule version: CMX_V2_4; inputs CNV_RETIRE_7B; annotation CMX_ANNOT_V1 "
    "(bash comment; busts the task cache)\n"
)

NF_CMD_OLD = "            ${purple_arg} \\\\\n"
NF_CMD_NEW = NF_CMD_OLD + "            ${annot_arg} \\\\\n"

# ---------------------------------------------------------------------------
# workflows/tspipe.nf
# ---------------------------------------------------------------------------

WF = "workflows/tspipe.nf"

WF_COMMENT_OLD = "params.cnv_noise_profile, params.cytoband, params.clingen are ignored"
WF_COMMENT_NEW = (
    "params.cytoband and params.clingen feed CMX_ANNOT_V1 "
    "(assets/references fallback); params.cnv_noise_profile is ignored"
)

WF_CH_OLD = (
    "        ch_cnv_gene_blacklist = file(gene_blacklist_path).exists() ? "
    "Channel.value(file(gene_blacklist_path)) : Channel.value([])\n"
)
WF_CH_NEW = WF_CH_OLD + (
    "        // CMX_ANNOT_V1: annotation assets -- params override, assets fallback, empty list when absent\n"
    '        def cytoband_path     = params.cytoband ?: "${projectDir}/assets/references/cytoBand_hg38.txt"\n'
    '        def clingen_path      = params.clingen  ?: "${projectDir}/assets/references/ClinGen_gene_curation_list_GRCh38.tsv"\n'
    '        def driver_panel_path = params.hmf_driver_panel ?: "${projectDir}/assets/${params.panel}/hmftools/DriverGenePanel.${params.panel}.38.tsv"\n'
    "        ch_cnv_cytoband     = file(cytoband_path).exists()     ? Channel.value(file(cytoband_path))     : Channel.value([])\n"
    "        ch_cnv_clingen      = file(clingen_path).exists()      ? Channel.value(file(clingen_path))      : Channel.value([])\n"
    "        ch_cnv_driver_panel = file(driver_panel_path).exists() ? Channel.value(file(driver_panel_path)) : Channel.value([])\n"
)

WF_CALL_OLD = (
    "        CNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female, "
    "ch_cnv_gene_blacklist )   // SEXSTRAT_V1 CNV_BLACKLIST_V1\n"
)
WF_CALL_NEW = (
    "        CNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female, "
    "ch_cnv_gene_blacklist,\n"
    "                             ch_cnv_cytoband, ch_cnv_clingen, ch_cnv_driver_panel )   "
    "// SEXSTRAT_V1 CNV_BLACKLIST_V1 CMX_ANNOT_V1\n"
)

# (path, old, new, mode); mode "replace" = exact once; "insert_before" = new + old;
# "insert_after_line" = old is a substring of exactly one line, new is appended after that line
EDITS = [
    (PY, PY_DOC_OLD, PY_DOC_NEW, "replace"),
    (PY, PY_LOADERS_ANCHOR, PY_LOADERS_NEW, "insert_before"),
    (PY, PY_ARGS_OLD, PY_ARGS_NEW, "replace"),
    (PY, PY_LOAD_ANCHOR, PY_LOAD_NEW, "insert_after_line"),
    (PY, PY_ANNOT_OLD, PY_ANNOT_NEW, "replace"),
    (PY, PY_COLS_OLD, PY_COLS_NEW, "replace"),
    (NF, NF_HDR_OLD, NF_HDR_NEW, "replace"),
    (NF, NF_IN_OLD, NF_IN_NEW, "replace"),
    (NF, NF_DEF_OLD, NF_DEF_NEW, "replace"),
    (NF, NF_CACHE_OLD, NF_CACHE_NEW, "replace"),
    (NF, NF_CMD_OLD, NF_CMD_NEW, "replace"),
    (WF, WF_COMMENT_OLD, WF_COMMENT_NEW, "replace"),
    (WF, WF_CH_OLD, WF_CH_NEW, "replace"),
    (WF, WF_CALL_OLD, WF_CALL_NEW, "replace"),
]


def apply_edit(text, old, new, mode):
    if mode == "insert_after_line":
        lines = text.split("\n")
        hits = [i for i, l in enumerate(lines) if old in l]
        if len(hits) != 1:
            return None, len(hits)
        lines.insert(hits[0] + 1, new.rstrip("\n"))
        return "\n".join(lines), 1
    n = text.count(old)
    if n != 1:
        return None, n
    repl = new + old if mode == "insert_before" else new
    return text.replace(old, repl, 1), 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    staged = {}
    skipped = []
    errors = []

    for rel, old, new, mode in EDITS:
        p = REPO / rel
        if rel in skipped:
            continue
        if rel not in staged:
            if not p.exists():
                errors.append("%s: file not found" % rel)
                continue
            text = p.read_text()
            if MARKER in text:
                print("SKIP  %s: %s already present" % (rel, MARKER))
                skipped.append(rel)
                continue
            staged[rel] = text
        out, n = apply_edit(staged[rel], old, new, mode)
        if out is None:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70]))
            continue
        staged[rel] = out

    if errors:
        print("ABORT -- nothing written:")
        for e in errors:
            print("  " + e)
        sys.exit(1)

    for rel, text in staged.items():
        orig = (REPO / rel).read_text()
        added = text.count("\n") - orig.count("\n")
        print("PLAN  %s: +%d lines, marker %s" % (rel, added, MARKER))

    if not args.apply:
        print("dry run; re-run with --apply")
        return

    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text())
        p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
