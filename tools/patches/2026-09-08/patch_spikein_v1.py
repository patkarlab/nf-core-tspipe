#!/usr/bin/env python3
"""tools/patches/2026-09-08/patch_spikein_v1.py -- MARKER SPIKEIN_V1 (D13)

Wires the spike-in tab end to end. New files (already copied into place):
  assets/twist_myeloid/spikein_regions.tsv, modules/local/spikein_sites.nf,
  bin/spikein_sites.py, bin/dashboard_builder/parsers/spikein.py.

This patcher edits seven existing files:
  subworkflows/local/preprocessing.nf   include + SPIKEIN_SITES call + withResolvedSex + emit
  workflows/tspipe.nf                   .join(PREPROCESSING.out.spikein) on ch_organize
  modules/local/organize_output.nf      input tuple, --spikein-snps arg, stub touch
  bin/organize_output.py                --spikein-snps argparse + hardlink into clinical/
  modules/local/dashboard.nf            --spikein-regions from assets/<panel>/spikein_regions.tsv
  bin/dashboard_builder/build.py        import, --spikein-regions, ctx["spikein"]
  bin/dashboard_builder/templates/sample_report.html.j2   nav item, tab pane, DataTable init

Every edit is insert-before / insert-after / replace of ONE line found by a
substring that must occur on exactly one line (anchors never span lines).
All anchors are validated before anything is written; a file that already
contains the MARKER is skipped. Dry-run by default; --apply writes with
.bak_spikein_v1_<timestamp> backups.

Usage:  python3 tools/patches/2026-09-08/patch_spikein_v1.py [--apply]
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

MARKER = "SPIKEIN_V1"
TAG = "spikein_v1"
REPO = Path(__file__).resolve().parents[3]

# (path, op, anchor_substring, text)   op: after | before | replace
# For 'replace', text replaces the whole anchored line (text may be multi-line).
EDITS = [
    # ---------------------------------------------------------------- preprocessing.nf
    ("subworkflows/local/preprocessing.nf", "after",
     "include { SEX_CHECK              } from '../../modules/local/sex_check'",
     "include { SPIKEIN_SITES          } from '../../modules/local/spikein_sites'   // MARKER SPIKEIN_V1\n"),
    ("subworkflows/local/preprocessing.nf", "before",
     "// MARKER SEX_CHECK_V1a: the map closure is replayed per consumer of ch_sex_by_id; log once.",
     "        // MARKER SPIKEIN_V1: germline spike-in SNP genotypes on the final BAM. Panels without\n"
     "        // assets/<panel>/spikein_regions.tsv stage [] and get a header-only table.\n"
     "        def spikein_asset_path = \"${projectDir}/assets/${params.panel}/spikein_regions.tsv\"\n"
     "        def spikein_asset_file = file(spikein_asset_path)\n"
     "        if( !spikein_asset_file.exists() )\n"
     "            log.info \"[SPIKEIN_SITES] no spike-in asset at ${spikein_asset_path}; header-only tables\"\n"
     "        ch_spikein_asset = Channel.value( spikein_asset_file.exists() ? spikein_asset_file : [] )\n"
     "        SPIKEIN_SITES(\n"
     "            ABRA2.out.bam,\n"
     "            reference_ch,\n"
     "            ch_spikein_asset\n"
     "        )\n"),
    ("subworkflows/local/preprocessing.nf", "after",
     "ch_sexed_sex_check = withResolvedSex(SEX_CHECK.out.tsv, ch_sex_by_id)",
     "        ch_sexed_spikein = withResolvedSex(SPIKEIN_SITES.out.tsv, ch_sex_by_id)   // SPIKEIN_V1\n"),
    ("subworkflows/local/preprocessing.nf", "after",
     "sex_check     = ch_sexed_sex_check",
     "        spikein       = ch_sexed_spikein   // SPIKEIN_V1\n"),

    # ---------------------------------------------------------------- tspipe.nf
    ("workflows/tspipe.nf", "after",
     ".join(RECONCNV.out.dir)",
     "        .join(PREPROCESSING.out.spikein)                                     // + spikein (SPIKEIN_V1)\n"),

    # ---------------------------------------------------------------- organize_output.nf
    ("modules/local/organize_output.nf", "replace",
     "path(reconcnv_dir)   // MARKER VIZ_V1 (MARKER VIZ_V1b: styled_scatter_dir removed)",
     "              path(reconcnv_dir),   // MARKER VIZ_V1 (MARKER VIZ_V1b: styled_scatter_dir removed)\n"
     "              path(spikein)   // MARKER SPIKEIN_V1: SPIKEIN_SITES genotype table\n"),
    ("modules/local/organize_output.nf", "after",
     "def reconcnv_dir_arg = reconcnv_dir ?",
     "        def spikein_arg = spikein ? \"--spikein-snps ${spikein}\" : ''   // SPIKEIN_V1\n"),
    ("modules/local/organize_output.nf", "replace",
     "            ${reconcnv_dir_arg}",
     "            ${reconcnv_dir_arg} \\\\\n"
     "            ${spikein_arg}\n"),
    ("modules/local/organize_output.nf", "after",
     "touch clinical/${meta.id}_dashboard.html",
     "        touch clinical/${meta.id}.spikein_snps.tsv\n"),

    # ---------------------------------------------------------------- organize_output.py
    ("bin/organize_output.py", "after",
     "parser.add_argument(\"--reconcnv-dir\"",
     "    parser.add_argument(\"--spikein-snps\", default=None, help=\"SPIKEIN_SITES genotype table (optional; SPIKEIN_V1)\")\n"),
    ("bin/organize_output.py", "before",
     "    # --- Summary ---",
     "    # --- Spike-in SNP genotypes (MARKER SPIKEIN_V1): top-level clinical/<sample>.spikein_snps.tsv ---\n"
     "    if present(args.spikein_snps):\n"
     "        hardlink(args.spikein_snps, out / Path(args.spikein_snps).name, \"spike-in SNP genotypes\")\n"
     "    else:\n"
     "        logger.info(\"skip (absent): spike-in SNP genotypes\")\n"
     "\n"),

    # ---------------------------------------------------------------- dashboard.nf
    ("modules/local/dashboard.nf", "after",
     "def known_low_arg = known_low.exists() ?",
     "        def spikein_asset = file(\"${projectDir}/assets/${params.panel}/spikein_regions.tsv\")   // SPIKEIN_V1\n"
     "        def spikein_arg   = spikein_asset.exists() ? \"--spikein-regions ${spikein_asset}\" : ''\n"),
    ("modules/local/dashboard.nf", "after",
     "            ${known_low_arg} \\\\",
     "            ${spikein_arg} \\\\\n"),

    # ---------------------------------------------------------------- build.py
    ("bin/dashboard_builder/build.py", "after",
     "from parsers import fastp as p_fastp",
     "from parsers import spikein as p_spikein   # SPIKEIN_V1\n"),
    ("bin/dashboard_builder/build.py", "after",
     "logging.warning(\"[%s] fastp parse failed: %s\", sample, exc)",
     "    ctx[\"spikein\"] = None   # SPIKEIN_V1: Spike-in tab renders only when the panel has the asset\n"
     "    if p_spikein.ASSET_PATH:\n"
     "        try:\n"
     "            ctx[\"spikein\"] = p_spikein.parse(\n"
     "                p_spikein.ASSET_PATH, coverage_path=cov_path,\n"
     "                snps_path=effective_dir / f\"{sample}.spikein_snps.tsv\",\n"
     "                filtered=ctx.get(\"filtered\"))\n"
     "        except Exception as exc:\n"
     "            logging.warning(\"[%s] spikein parse failed: %s\", sample, exc)\n"),
    ("bin/dashboard_builder/build.py", "before",
     "    args = parser.parse_args()",
     "    parser.add_argument(\n"
     "        \"--spikein-regions\", dest=\"spikein_regions\", default=None,\n"
     "        help=\"spikein_regions.tsv for the panel: non-exonic spike-in regions and germline \"\n"
     "             \"SNP sites shown on the Spike-in tab. Optional.\"   # SPIKEIN_V1\n"
     "    )\n"),
    ("bin/dashboard_builder/build.py", "after",
     "p_coverage.KNOWN_LOW_EXONS_PATH = args.known_low_exons",
     "    p_spikein.ASSET_PATH = args.spikein_regions   # SPIKEIN_V1\n"),

    # ---------------------------------------------------------------- template
    ("bin/dashboard_builder/templates/sample_report.html.j2", "after",
     "data-bs-target=\"#tab-blacklist\"",
     "      {# SPIKEIN_V1 (D13) #}\n"
     "      {% if ctx.spikein %}\n"
     "      <li class=\"nav-item\"><button class=\"nav-link\"        data-bs-toggle=\"pill\" data-bs-target=\"#tab-spikein\" type=\"button\" role=\"tab\">"
     "Spike-in <span class=\"badge bg-secondary ms-1\">{{ ctx.spikein.n_variants }}</span></button></li>\n"
     "      {% endif %}\n"),
    ("bin/dashboard_builder/templates/sample_report.html.j2", "before",
     "id=\"tab-filtered\" role=\"tabpanel\"",
     "      {# ===== Spike-in tab (SPIKEIN_V1, D13) ===== #}\n"
     "      {% if ctx.spikein %}\n"
     "      <div class=\"tab-pane fade\" id=\"tab-spikein\" role=\"tabpanel\">\n"
     "        <h4>Spike-in regions and germline risk SNPs</h4>\n"
     "        <p class=\"text-muted small mb-2\">\n"
     "          Non-exonic targets of the panel (<code>assets/&lt;panel&gt;/spikein_regions.tsv</code>): regulatory regions whose calls the\n"
     "          consequence filter keeps out of the clinical table, and germline B-ALL risk SNPs genotyped directly from the BAM.\n"
     "          Region coverage is the mean over the interval (duplicates included) against the {{ ctx.spikein.tier_x }}x reportability tier.\n"
     "          Every <code>somaticseq.filtered.tsv</code> call inside a region is listed with its Filter value; none of it has been reviewed for\n"
     "          reporting. SNP genotypes are germline calls read from a tumour sample: a copy-number change or copy-neutral LOH on that\n"
     "          chromosome can shift the allele fraction. Sites below {{ ctx.spikein.min_depth }}x are not called.\n"
     "        </p>\n"
     "\n"
     "        <h5 class=\"mt-3\">Regions</h5>\n"
     "        <div class=\"table-responsive\">\n"
     "          <table id=\"spikein-regions-table\" class=\"table table-sm table-striped w-100\">\n"
     "            <thead><tr><th>region</th><th>gene</th><th>interval (hg38)</th><th>bp</th><th>mean cov</th><th>&ge;100x %</th><th>&ge;250x %</th><th>&ge;500x %</th><th>{{ ctx.spikein.tier_x }}x</th><th>calls</th><th>note</th></tr></thead>\n"
     "            <tbody>\n"
     "            {% for r in ctx.spikein.regions %}\n"
     "              <tr><td>{{ r.name }}</td><td>{{ r.gene }}</td><td class=\"text-nowrap\">{{ r.chrom }}:{{ r.start }}-{{ r.end }}</td><td>{{ r.length }}</td>\n"
     "                  <td>{{ '%.0f' | format(r.mean_cov) if r.mean_cov is not none else 'n/a' }}</td>\n"
     "                  <td>{{ r.pct_100x if r.pct_100x is not none else '' }}</td><td>{{ r.pct_250x if r.pct_250x is not none else '' }}</td><td>{{ r.pct_500x if r.pct_500x is not none else '' }}</td>\n"
     "                  <td>{% if r.at_tier is none %}<span class=\"badge bg-secondary\">no coverage row</span>{% elif r.at_tier %}<span class=\"badge bg-success\">PASS</span>{% else %}<span class=\"badge bg-warning text-dark\">BELOW</span>{% endif %}</td>\n"
     "                  <td>{{ r.variants | length }}</td><td class=\"small\">{{ r.description }}</td></tr>\n"
     "            {% endfor %}\n"
     "            </tbody>\n"
     "          </table>\n"
     "        </div>\n"
     "\n"
     "        <h5 class=\"mt-3\">Calls inside spike-in regions <span class=\"badge bg-secondary\">{{ ctx.spikein.n_variants }}</span></h5>\n"
     "        {% if ctx.spikein.region_variants %}\n"
     "          <div class=\"table-responsive\">\n"
     "            <table id=\"spikein-variants-table\" class=\"table table-sm table-striped table-hover w-100\">\n"
     "              <thead><tr><th>region</th><th>gene</th><th>position</th><th>HGVSc</th><th>HGVSp</th><th>consequence</th><th>class</th><th>VAF %</th><th>callers</th><th>n</th><th>Max AF</th><th>ClinVar</th><th>Filter</th></tr></thead>\n"
     "              <tbody>\n"
     "              {% for v in ctx.spikein.region_variants %}\n"
     "                <tr><td>{{ v.region }}</td><td>{{ v.Gene }}</td><td class=\"text-nowrap\">{{ v.Chr }}:{{ v.Start }} {{ v.Ref }}&gt;{{ v.Alt }}</td>\n"
     "                    <td>{{ v.HGVSc }}</td><td>{{ v.HGVSp }}</td><td class=\"small\">{{ v.Consequence }}</td><td>{{ v.Variant_Class }}</td>\n"
     "                    <td>{{ v.VAF_pct }}</td><td class=\"small\">{{ v.Callers }}</td><td>{{ v.VariantCaller_Count }}</td>\n"
     "                    <td>{{ v.Max_AF }}</td><td class=\"small\">{{ v.ClinVar_Significance }}</td>\n"
     "                    <td>{% if v.Filter == 'PASS' %}<span class=\"badge bg-success\">PASS</span>{% else %}<span class=\"badge bg-light text-dark border\">{{ v.Filter }}</span>{% endif %}</td></tr>\n"
     "              {% endfor %}\n"
     "              </tbody>\n"
     "            </table>\n"
     "          </div>\n"
     "        {% else %}\n"
     "          <div class=\"tspipe-empty\">No calls inside the spike-in regions in this sample.</div>\n"
     "        {% endif %}\n"
     "\n"
     "        <h5 class=\"mt-3\">Germline risk SNP genotypes</h5>\n"
     "        <div class=\"table-responsive\">\n"
     "          <table id=\"spikein-snps-table\" class=\"table table-sm table-striped w-100\">\n"
     "            <thead><tr><th>site</th><th>rsID</th><th>gene</th><th>position (hg38)</th><th>ref</th><th>alt</th><th>ref n</th><th>alt n</th><th>depth</th><th>alt AF</th><th>genotype</th><th>risk allele</th><th>risk copies</th><th>status</th><th>caller Filter</th></tr></thead>\n"
     "            <tbody>\n"
     "            {% for s in ctx.spikein.snps %}\n"
     "              <tr><td>{{ s.name }}</td><td>{{ s.rsid }}{% if s.rsid_alias and s.rsid_alias != '-' %} <span class=\"text-muted small\">({{ s.rsid_alias }})</span>{% endif %}</td><td>{{ s.gene }}</td>\n"
     "                  <td class=\"text-nowrap\">{{ s.chrom }}:{{ s.pos }}</td><td>{{ s.ref if s.ref is defined else '' }}</td><td>{{ s.alt if s.alt is defined else '' }}</td>\n"
     "                  <td>{{ s.ref_count if s.ref_count is defined else '' }}</td><td>{{ s.alt_count if s.alt_count is defined else '' }}</td><td>{{ s.depth if s.depth is defined else '' }}</td><td>{{ s.alt_af if s.alt_af is defined else '' }}</td>\n"
     "                  <td>{% if s.genotype is defined and s.genotype != '-' %}<span class=\"badge {% if s.genotype == 'het' %}bg-info text-dark{% elif s.genotype == 'hom_alt' %}bg-primary{% else %}bg-secondary{% endif %}\">{{ s.genotype }}</span>{% endif %}</td>\n"
     "                  <td>{{ s.risk_allele }}</td>\n"
     "                  <td>{% if s.risk_copies is defined and s.risk_copies in ['1', '2'] %}<span class=\"badge bg-warning text-dark\">{{ s.risk_copies }}</span>{% elif s.risk_copies is defined %}{{ s.risk_copies }}{% endif %}</td>\n"
     "                  <td>{% if s.status == 'OK' %}<span class=\"badge bg-success\">OK</span>{% else %}<span class=\"badge bg-warning text-dark\">{{ s.status }}</span>{% endif %}</td>\n"
     "                  <td class=\"small\">{% if s.filtered_row %}{{ s.filtered_row.Filter }} ({{ s.filtered_row.VAF_pct }}%){% else %}not called{% endif %}</td></tr>\n"
     "            {% endfor %}\n"
     "            </tbody>\n"
     "          </table>\n"
     "        </div>\n"
     "      </div>\n"
     "      {% endif %}\n"
     "\n"),
    ("bin/dashboard_builder/templates/sample_report.html.j2", "after",
     "blacklist-table').DataTable",
     "    if ($('#spikein-variants-table').length) { $('#spikein-variants-table').DataTable({ pageLength: 25, order: [] }); }   // SPIKEIN_V1\n"),
]


def find_line(lines, anchor, path):
    hits = [i for i, l in enumerate(lines) if anchor in l]
    if len(hits) != 1:
        raise RuntimeError("%s: anchor matched %d lines (need exactly 1): %r" % (path, len(hits), anchor))
    return hits[0]


def plan(repo):
    """Return {path: new_text} after validating every anchor against the on-disk files."""
    by_file = {}
    for rel, op, anchor, text in EDITS:
        by_file.setdefault(rel, []).append((op, anchor, text))
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
        # validate all anchors first against the untouched file
        for op, anchor, text in edits:
            find_line(lines, anchor, rel)
        # apply sequentially; each anchor is re-found in the evolving text
        for op, anchor, text in edits:
            i = find_line(lines, anchor, rel)
            new = text.splitlines(keepends=True)
            if op == "after":
                lines[i + 1:i + 1] = new
            elif op == "before":
                lines[i:i] = new
            elif op == "replace":
                lines[i:i + 1] = new
            else:
                raise RuntimeError("bad op %s" % op)
        out[rel] = "".join(lines)
        print("[patch]  %s: %d edit(s)" % (rel, len(edits)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write files (default: dry-run)")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    repo = Path(args.repo)
    try:
        planned = plan(repo)
    except RuntimeError as exc:
        print("[error]  %s" % exc)
        print("[error]  nothing written")
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
