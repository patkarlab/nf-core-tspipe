#!/usr/bin/env python3
"""tools/patches/2026-09-08/patch_igv_spikein_v1.py -- MARKER SPIKEIN_V1d (D13b-2)

IGV_REPORTS renders the spike-in region calls in addition to the clinical
table, so the IGV chips on the dashboard's Spike-in tab resolve. Three edits:

  bin/igv_reports.py           --extra-input (filtered TSV) + --spikein-regions (asset):
                               filtered rows inside a regulatory region are appended to
                               the site list, de-duplicated against the clinical rows
  modules/local/igv_reports.nf input tuple gains path(filtered_tsv); new value input
                               spikein_asset ([] when absent); args passed only when set
  workflows/tspipe.nf          IGV_REPORTS(clinical.join(bam).join(filtered), ch_reference,
                               asset-or-[])

Anchors are single-line substrings that must occur exactly once (a two-line
anchor must match as a contiguous pair). All are validated before anything is
written; a file already carrying the MARKER is skipped. Dry-run by default;
--apply writes with .bak_spikein_v1d_<timestamp> backups.

Cost: IGV_REPORTS 8 + ORGANIZE_OUTPUT 8 + DASHBOARD + REPORT_BUNDLE (18 tasks).
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

MARKER = "SPIKEIN_V1d"
TAG = "spikein_v1d"
REPO = Path(__file__).resolve().parents[3]

EDITS = [
    # ---------------------------------------------------------------- igv_reports.py
    ("bin/igv_reports.py", "after",
     'parser.add_argument("-s", "--sample", required=True, help="Sample name")',
     '    parser.add_argument("--extra-input", default=None,\n'
     '                        help="Filtered TSV (same columns); rows inside --spikein-regions are added (SPIKEIN_V1d)")\n'
     '    parser.add_argument("--spikein-regions", default=None,\n'
     '                        help="assets/<panel>/spikein_regions.tsv; regulatory rows define the regions (SPIKEIN_V1d)")\n'),
    ("bin/igv_reports.py", "after",
     'log.info("Read %d clinical variants from %s", len(rows), args.input)',
     "\n"
     "    # SPIKEIN_V1d (D13b-2): filtered-table calls inside the spike-in regions join the site list so\n"
     "    # the dashboard's Spike-in tab IGV chips resolve; de-duplicated against the clinical rows.\n"
     "    if args.extra_input and args.spikein_regions:\n"
     "        regions = []\n"
     "        with open(args.spikein_regions) as fh:\n"
     "            header = None\n"
     "            for line in fh:\n"
     "                line = line.rstrip(\"\\n\")\n"
     "                if not line or line.startswith(\"#\"):\n"
     "                    continue\n"
     "                parts = line.split(\"\\t\")\n"
     "                if header is None:\n"
     "                    header = parts\n"
     "                    continue\n"
     "                rec = dict(zip(header, parts))\n"
     "                if rec.get(\"class\") == \"regulatory\":\n"
     "                    regions.append((rec[\"chrom\"], int(rec[\"start\"]), int(rec[\"end\"])))\n"
     "        have = {(r[\"Chr\"], r[\"Start\"], r[\"Ref\"], r[\"Alt\"]) for r in rows}\n"
     "        extra = []\n"
     "        for r in read_clinical_tsv(args.extra_input):\n"
     "            try:\n"
     "                pos = int(r[\"Start\"])\n"
     "            except (KeyError, ValueError):\n"
     "                continue\n"
     "            if any(r[\"Chr\"] == c and s < pos <= e for c, s, e in regions):\n"
     "                key = (r[\"Chr\"], r[\"Start\"], r[\"Ref\"], r[\"Alt\"])\n"
     "                if key not in have:\n"
     "                    have.add(key)\n"
     "                    extra.append(r)\n"
     "        rows.extend(extra)\n"
     "        log.info(\"SPIKEIN_V1d: added %d spike-in region call(s) from %s (%d regions)\",\n"
     "                 len(extra), args.extra_input, len(regions))\n"),

    # ---------------------------------------------------------------- igv_reports.nf
    ("modules/local/igv_reports.nf", "replace",
     "        tuple val(meta), path(clinical_tsv), path(bam), path(bai)",
     "        tuple val(meta), path(clinical_tsv), path(bam), path(bai), path(filtered_tsv)   // SPIKEIN_V1d\n"),
    ("modules/local/igv_reports.nf", "after",
     "        tuple path(fasta), path(fai), path(dict)",
     "        path spikein_asset   // SPIKEIN_V1d: assets/<panel>/spikein_regions.tsv, or [] when the panel has none\n"),
    ("modules/local/igv_reports.nf", "after",
     "    script:",
     "        def spikein_args = spikein_asset ? \"--extra-input ${filtered_tsv} --spikein-regions ${spikein_asset}\" : ''   // SPIKEIN_V1d\n"),
    ("modules/local/igv_reports.nf", "replace",
     "            --output  ${meta.id}_igv_report.html",
     "            --output  ${meta.id}_igv_report.html \\\\\n"
     "            ${spikein_args}\n"),

    # ---------------------------------------------------------------- tspipe.nf
    ("workflows/tspipe.nf", "replace",
     "        ANNOTATION.out.clinical_tsv.join(PREPROCESSING.out.final_bam),\n        ch_reference",
     "        ANNOTATION.out.clinical_tsv.join(PREPROCESSING.out.final_bam).join(ANNOTATION.out.filtered_tsv),   // SPIKEIN_V1d\n"
     "        ch_reference,\n"
     "        ch_igv_spikein\n"),
    ("workflows/tspipe.nf", "before",
     "    // ----- 6b. IGV_REPORTS: per-sample HTML for clinical review (D2) -----",
     "    // SPIKEIN_V1d (D13b-2): spike-in region calls join the IGV report so the Spike-in tab chips resolve\n"
     "    def igv_spikein_file = file(\"${projectDir}/assets/${params.panel}/spikein_regions.tsv\")\n"
     "    ch_igv_spikein = Channel.value( igv_spikein_file.exists() ? igv_spikein_file : [] )\n"
     "\n"),
]


def find_lines(lines, anchor):
    if "\n" in anchor:
        parts = anchor.split("\n")
        hits = [i for i in range(len(lines) - len(parts) + 1)
                if all(parts[k] in lines[i + k] for k in range(len(parts)))]
        return hits, len(parts)
    return [i for i, l in enumerate(lines) if anchor in l], 1


def plan(repo):
    by_file = {}
    for e in EDITS:
        by_file.setdefault(e[0], []).append(e)
    out = {}
    for rel, edits in by_file.items():
        p = repo / rel
        if not p.exists():
            raise RuntimeError("missing file: %s" % p)
        src = p.read_text()
        if MARKER in src:
            print("[skip]   %s already carries %s" % (rel, MARKER))
            continue
        lines = src.splitlines(keepends=True)
        for _, op, anchor, text in edits:
            hits, _span = find_lines(lines, anchor)
            if len(hits) != 1:
                raise RuntimeError("%s: anchor matched %d (need 1): %r" % (rel, len(hits), anchor[:60]))
        for _, op, anchor, text in edits:
            hits, span = find_lines(lines, anchor)
            i = hits[0]
            new = text.splitlines(keepends=True)
            if op == "after":
                lines[i + span:i + span] = new
            elif op == "before":
                lines[i:i] = new
            elif op == "replace":
                lines[i:i + span] = new
        out[rel] = "".join(lines)
        print("[patch]  %s: %d edit(s)" % (rel, len(edits)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    repo = Path(args.repo)
    try:
        planned = plan(repo)
    except RuntimeError as exc:
        print("[error]  %s\n[error]  nothing written" % exc)
        return 1
    if not planned:
        print("[done]   nothing to do")
        return 0
    if not args.apply:
        print("[dry]    %d file(s) would change; re-run with --apply" % len(planned))
        return 0
    ts = time.strftime("%Y%m%d_%H%M%S")
    for rel, new in planned.items():
        p = repo / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, ts))
        shutil.copy2(p, bak)
        print("[backup] %s" % bak.relative_to(repo))
        p.write_text(new)
        print("[write]  %s" % rel)
    print("[done]   %d file(s) patched with %s" % (len(planned), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
