#!/usr/bin/env python3
"""
render_dashboard.py - Per-sample QC dashboard renderer.

Reads:
  - Per-exon coverage TSV (from PARSE_EXON_COVERAGE)
  - Picard CollectHsMetrics output text file (from HSMETRICS)

Writes one self-contained HTML file: matplotlib chart embedded as
base64 PNG, CSS in <style> tags, no external assets, no JS framework.

USAGE:
    python3 render_dashboard.py \
        --sample        25NGS1307 \
        --exon-coverage 25NGS1307_exon_coverage.tsv \
        --hsmetrics     25NGS1307_hsmetrics.txt \
        --output        25NGS1307_dashboard.html \
        --commit-sha    178cc08 \
        --run-date      2026-05-17 \
        [--panel-name   "MYOPOOL hg38"]
"""

import argparse
import base64
import csv
import io
import sys
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


COV_RED_MAX    = 100
COV_AMBER_MAX  = 250

COLOR_GREEN  = "#4a7c4e"
COLOR_AMBER  = "#c98a3f"
COLOR_RED    = "#b54848"
COLOR_INK    = "#1a1a1a"
COLOR_PAPER  = "#fafaf7"


def parse_exon_coverage_tsv(path):
    rows = []
    with path.open("r", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            r["Mean_Coverage"] = float(r["Mean_Coverage"])
            r["Length_bp"]     = int(r["Length_bp"])
            for k in ("Pct_100x", "Pct_250x", "Pct_500x"):
                r[k] = float(r[k])
            r["Flag"] = r.get("Flag", "").strip()
            rows.append(r)
    return rows


def parse_hsmetrics(path: Path) -> dict:
    lines = path.read_text().splitlines()
    marker_idx = None
    for i, line in enumerate(lines):
        if "METRICS CLASS" in line and "HsMetrics" in line:
            marker_idx = i
            break
    if marker_idx is None:
        raise ValueError(f"Could not find HsMetrics METRICS CLASS line in {path}")

    header, data = None, None
    for j in range(marker_idx + 1, len(lines)):
        line = lines[j].rstrip()
        if not line:
            continue
        if header is None:
            header = line.split("\t")
            continue
        data = line.split("\t")
        break
    if header is None or data is None:
        raise ValueError(f"Could not parse HsMetrics data rows in {path}")

    metrics = dict(zip(header, data))
    coerced = {}
    for k, v in metrics.items():
        if v in ("", "?"):
            coerced[k] = None
            continue
        try:
            coerced[k] = float(v) if "." in v or "e" in v.lower() else int(v)
        except ValueError:
            coerced[k] = v
    return coerced


def per_gene_rollup(exon_rows):
    by_gene = defaultdict(list)
    for r in exon_rows:
        by_gene[r["Gene"]].append(r)

    out = []
    for gene in sorted(by_gene.keys(), key=lambda g: g.lower()):
        rows = by_gene[gene]
        covs = [r["Mean_Coverage"] for r in rows]
        n = len(rows)
        out.append({
            "Gene": gene,
            "n_exons": n,
            "mean_cov": sum(covs) / n if n else 0.0,
            "min_cov":  min(covs) if covs else 0.0,
            "max_cov":  max(covs) if covs else 0.0,
            "pct_exons_100": 100.0 * sum(1 for c in covs if c >= 100) / n if n else 0.0,
            "pct_exons_250": 100.0 * sum(1 for c in covs if c >= 250) / n if n else 0.0,
            "low_cov_exons": sum(1 for r in rows if r["Flag"] == "LOW_COVERAGE"),
        })
    return out


def low_coverage_exons(exon_rows):
    flagged = [r for r in exon_rows if r["Flag"] == "LOW_COVERAGE"]
    return sorted(flagged, key=lambda r: r["Mean_Coverage"])


def coverage_color(cov: float) -> str:
    if cov < COV_RED_MAX:    return COLOR_RED
    if cov < COV_AMBER_MAX:  return COLOR_AMBER
    return COLOR_GREEN


def render_per_gene_chart(per_gene,
                          reference_coverage,
                          reference_label="mean of exon means"):
    genes = [g["Gene"] for g in per_gene]
    means = [g["mean_cov"] for g in per_gene]
    colors = [coverage_color(m) for m in means]

    n = len(genes)
    fig_w = max(14, n * 0.12)
    fig, ax = plt.subplots(figsize=(fig_w, 5.5), dpi=110)

    x = list(range(n))
    ax.bar(x, means, color=colors, width=0.78, edgecolor="none")

    ax.axhline(COV_RED_MAX,   color=COLOR_RED,   linestyle=":", linewidth=0.8, alpha=0.45)
    ax.axhline(COV_AMBER_MAX, color=COLOR_AMBER, linestyle=":", linewidth=0.8, alpha=0.45)

    if reference_coverage and reference_coverage > 0:
        ax.axhline(reference_coverage, color=COLOR_INK,
                   linestyle="--", linewidth=1.2, alpha=0.75, zorder=5)
        ax.text(n - 0.5, reference_coverage,
                f"  {reference_label}\n  {int(round(reference_coverage)):,}\u00d7",
                ha="left", va="center", fontsize=8.5,
                fontfamily="serif", color=COLOR_INK,
                bbox=dict(facecolor=COLOR_PAPER, edgecolor="none", pad=2.5, alpha=0.92))

    ax.set_xticks(x)
    ax.set_xticklabels(genes, rotation=75, ha="right", fontsize=7,
                       fontfamily="serif", color="#2a2a2a")
    ax.set_ylabel("Per-gene mean coverage (\u00d7)",
                  fontsize=10, fontfamily="serif", color="#2a2a2a")

    nonzero = [m for m in means if m > 0]
    if nonzero and max(means) / max(min(nonzero), 1) > 200:
        ax.set_yscale("symlog", linthresh=100)
    ymax = max(means) if means else 1
    if reference_coverage:
        ymax = max(ymax, reference_coverage)
    ax.set_ylim(0, ymax * 1.15)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#a0a0a0")
        ax.spines[s].set_linewidth(0.7)
    ax.tick_params(axis="both", which="both", length=2, colors="#666666", labelsize=7)
    ax.grid(axis="y", color="#e8e6e0", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    legend_elements = [
        Patch(facecolor=COLOR_GREEN, edgecolor="none", label=f"\u2265 {COV_AMBER_MAX}\u00d7"),
        Patch(facecolor=COLOR_AMBER, edgecolor="none", label=f"{COV_RED_MAX}\u2013{COV_AMBER_MAX}\u00d7"),
        Patch(facecolor=COLOR_RED,   edgecolor="none", label=f"< {COV_RED_MAX}\u00d7"),
    ]
    leg = ax.legend(handles=legend_elements, loc="upper left",
                    frameon=False, fontsize=8, ncol=3,
                    handlelength=1.4, handleheight=0.9, columnspacing=1.2)
    for text in leg.get_texts():
        text.set_color("#3a3a3a")
        text.set_fontfamily("serif")

    fig.tight_layout(pad=0.6, rect=[0, 0, 0.92, 1])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=COLOR_PAPER)
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


CSS = """
:root {
    --bg: #fafaf7; --paper: #ffffff;
    --ink: #1a1a1a; --ink-soft: #4a4a44;
    --rule: #e8e6e0; --rule-strong: #d4d1c8;
    --green: #4a7c4e; --amber: #c98a3f; --red: #b54848;
    --serif: "Iowan Old Style", "Apple Garamond", Baskerville,
             "Times New Roman", Times, serif;
    --sans:  -apple-system, BlinkMacSystemFont, "Segoe UI",
             "Helvetica Neue", Helvetica, Arial, sans-serif;
}
html, body {
    margin: 0; padding: 0;
    background: var(--bg); color: var(--ink);
    font-family: var(--serif); font-size: 15px; line-height: 1.55;
    -webkit-font-smoothing: antialiased;
}
.page { max-width: 1180px; margin: 0 auto; padding: 48px 56px 32px; }

header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 1.5px solid var(--ink);
    padding-bottom: 18px; margin-bottom: 36px;
}
.sample-name {
    font-family: var(--serif); font-size: 38px; font-weight: 600;
    letter-spacing: -0.02em; line-height: 1.1;
}
.summary-line {
    font-family: var(--sans); font-size: 12px; color: var(--ink-soft);
    letter-spacing: 0.04em; margin-top: 6px;
}
.report-title {
    font-family: var(--serif); font-size: 14px;
    letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-soft);
}

/* Hero strip */
.hero {
    display: grid;
    grid-template-columns: 2fr 2.4fr 1fr;
    gap: 0;
    border: 0.5px solid var(--rule-strong);
    background: var(--paper);
    margin-bottom: 44px;
}
.hero-cell {
    padding: 28px 30px; border-right: 0.5px solid var(--rule);
    position: relative; min-height: 140px;
}
.hero-cell:last-child { border-right: none; }
.hero .key {
    font-family: var(--sans); font-size: 10.5px;
    letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--ink-soft); margin-bottom: 12px;
}
.hero .value {
    font-family: var(--serif); font-weight: 600;
    letter-spacing: -0.02em; line-height: 1;
}
.hero .median  .value { font-size: 56px; }
.hero .lowcov  .value { font-size: 48px; }
.hero .offbait .value { font-size: 30px; }
.hero .detail {
    font-family: var(--sans); font-size: 11px;
    color: var(--ink-soft); margin-top: 10px; line-height: 1.45;
}
.hero .lowcov.has-lowcov .value { color: var(--red); }
.hero .lowcov.no-lowcov  .value { color: var(--green); }
.hero .lowcov-list {
    font-family: var(--sans); font-size: 11.5px; color: var(--ink);
    margin-top: 12px; line-height: 1.7;
}
.hero .lowcov-list .exon {
    font-variant-numeric: tabular-nums; color: var(--red); font-weight: 600;
}

section { margin: 0 0 40px; }
section h2 {
    font-family: var(--serif); font-size: 12.5px;
    font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--ink-soft);
    margin: 0 0 16px; padding-bottom: 8px;
    border-bottom: 0.5px solid var(--rule-strong);
}
.chart-frame {
    background: var(--paper); border: 0.5px solid var(--rule-strong);
    padding: 18px;
}
.chart-frame img { display: block; width: 100%; height: auto; }

.gene-table {
    width: 100%; border-collapse: collapse;
    background: var(--paper); font-family: var(--sans); font-size: 13px;
    border: 0.5px solid var(--rule-strong);
}
.gene-table thead th {
    text-align: left;
    font-family: var(--serif); font-size: 10.5px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-soft);
    padding: 14px 14px; background: #f4f2eb;
    border-bottom: 1px solid var(--rule-strong);
}
.gene-table tbody td {
    padding: 9px 14px; border-bottom: 0.5px solid var(--rule);
    font-variant-numeric: tabular-nums;
}
.gene-table tbody tr:last-child td { border-bottom: none; }
.gene-table tbody tr.has-low-cov { background: #fbeeee; }
.gene-table .gene-name { font-family: var(--serif); font-weight: 600; }
.gene-table .num { text-align: right; }
.gene-table .pill {
    display: inline-block; padding: 1px 9px; border-radius: 10px;
    font-size: 11px; font-weight: 600; font-family: var(--sans);
    letter-spacing: 0.04em; background: var(--red); color: white;
}

footer {
    margin-top: 48px; padding-top: 18px;
    border-top: 0.5px solid var(--rule-strong);
    font-family: var(--sans); font-size: 11px;
    color: var(--ink-soft); letter-spacing: 0.04em;
}
footer .prov-row { display: flex; gap: 26px; flex-wrap: wrap; align-items: center; }
footer .prov-row span { font-variant-numeric: tabular-nums; }
footer .prov-row .key {
    text-transform: uppercase; letter-spacing: 0.14em;
    font-size: 10px; color: #888; margin-right: 6px;
}

@media print {
    .page { padding: 24px 32px; }
    .hero, .chart-frame { break-inside: avoid; }
    .gene-table tr { break-inside: avoid; }
}
"""


def render_hero(*, mean_of_exon_means, exon_rows, hsmetrics) -> str:
    low_exons = low_coverage_exons(exon_rows)
    n_low = len(low_exons)

    if mean_of_exon_means is None or mean_of_exon_means <= 0:
        cov_display = "\u2014"
        cov_detail = "exon coverage TSV empty"
    else:
        cov_display = f"{int(round(mean_of_exon_means)):,}\u00d7"
        cov_detail = f"mean of {len(exon_rows)} per-exon means \u00b7 duplicates included"

    cov_html = (
        '<div class="hero-cell median">'
        '<div class="key">Mean coverage</div>'
        f'<div class="value">{escape(cov_display)}</div>'
        f'<div class="detail">{escape(cov_detail)}</div>'
        '</div>'
    )

    if n_low == 0:
        lowcov_html = (
            '<div class="hero-cell lowcov no-lowcov">'
            '<div class="key">Low-coverage exons (&lt; 100\u00d7)</div>'
            '<div class="value">0</div>'
            '<div class="detail">All exons \u2265 100\u00d7</div>'
            '</div>'
        )
    else:
        items = [
            f'<div><span class="exon">{escape(r["Gene"])} {escape(r["Exon"])}</span> '
            f'<span style="color:var(--ink-soft)">{r["Mean_Coverage"]:.0f}\u00d7</span></div>'
            for r in low_exons[:8]
        ]
        more = f'<div style="color:var(--ink-soft)">+{n_low-8} more</div>' if n_low > 8 else ''
        lowcov_html = (
            '<div class="hero-cell lowcov has-lowcov">'
            '<div class="key">Low-coverage exons (&lt; 100\u00d7)</div>'
            f'<div class="value">{n_low}</div>'
            f'<div class="lowcov-list">{"".join(items)}{more}</div>'
            '</div>'
        )

    off_bait = hsmetrics.get("PCT_OFF_BAIT")
    if off_bait is None:
        offbait_display, offbait_detail = "\u2014", "PCT_OFF_BAIT missing"
    else:
        try:
            offbait_pct = float(off_bait) * 100
            offbait_display = f"{offbait_pct:.1f}%"
            offbait_detail = "of aligned bases (Picard PCT_OFF_BAIT)"
        except (TypeError, ValueError):
            offbait_display, offbait_detail = "\u2014", "non-numeric"

    offbait_html = (
        '<div class="hero-cell offbait">'
        '<div class="key">Off-bait</div>'
        f'<div class="value">{escape(offbait_display)}</div>'
        f'<div class="detail">{escape(offbait_detail)}</div>'
        '</div>'
    )

    return f'<div class="hero">{cov_html}{lowcov_html}{offbait_html}</div>'


def render_gene_table(per_gene):
    head = (
        '<table class="gene-table"><thead><tr>'
        '<th>Gene</th>'
        '<th class="num">Exons</th>'
        '<th class="num">Mean cov</th>'
        '<th class="num">Min exon</th>'
        '<th class="num">% exons \u2265100\u00d7</th>'
        '<th class="num">% exons \u2265250\u00d7</th>'
        '<th>Flags</th>'
        '</tr></thead><tbody>'
    )
    rows = []
    for g in per_gene:
        cls = "has-low-cov" if g["low_cov_exons"] > 0 else ""
        flag_html = (
            f'<span class="pill">{g["low_cov_exons"]} low-cov</span>'
            if g["low_cov_exons"] > 0 else ""
        )
        rows.append(
            f'<tr class="{cls}">'
            f'<td class="gene-name">{escape(g["Gene"])}</td>'
            f'<td class="num">{g["n_exons"]}</td>'
            f'<td class="num">{int(round(g["mean_cov"])):,}\u00d7</td>'
            f'<td class="num">{int(round(g["min_cov"])):,}\u00d7</td>'
            f'<td class="num">{g["pct_exons_100"]:.0f}%</td>'
            f'<td class="num">{g["pct_exons_250"]:.0f}%</td>'
            f'<td>{flag_html}</td>'
            '</tr>'
        )
    return head + "".join(rows) + "</tbody></table>"


def render_html(*, sample, panel_name, exon_rows, hsmetrics, per_gene,
                chart_data_uri, commit_sha, run_date,
                mean_of_exon_means) -> str:
    summary_line = f"{len(per_gene)} genes \u00b7 {len(exon_rows)} exons"
    hero_html = render_hero(
        mean_of_exon_means=mean_of_exon_means,
        exon_rows=exon_rows,
        hsmetrics=hsmetrics,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>QC Dashboard \u2014 {escape(sample)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">

  <header>
    <div>
      <div class="sample-name">{escape(sample)}</div>
      <div class="summary-line">{escape(summary_line)}</div>
    </div>
    <div class="report-title">{escape(panel_name)} \u00b7 QC report</div>
  </header>

  {hero_html}

  <section>
    <h2>Per-gene coverage</h2>
    <div class="chart-frame">
      <img src="{chart_data_uri}" alt="Per-gene mean coverage">
    </div>
  </section>

  <section>
    <h2>Gene-level summary</h2>
    {render_gene_table(per_gene)}
  </section>

  <footer>
    <div class="prov-row">
      <span><span class="key">Sample</span>{escape(sample)}</span>
      <span><span class="key">Run date</span>{escape(run_date)}</span>
      <span><span class="key">Commit</span>{escape(commit_sha)}</span>
    </div>
  </footer>

</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--exon-coverage", type=Path, required=True)
    ap.add_argument("--hsmetrics", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--panel-name", default="MYOPOOL hg38")
    ap.add_argument("--commit-sha", default="(unspecified)")
    ap.add_argument("--run-date", default=datetime.now().strftime("%Y-%m-%d"))
    args = ap.parse_args()

    if not args.exon_coverage.is_file():
        print(f"ERROR: exon coverage TSV not found: {args.exon_coverage}", file=sys.stderr)
        return 2
    if not args.hsmetrics.is_file():
        print(f"ERROR: hsmetrics file not found: {args.hsmetrics}", file=sys.stderr)
        return 2

    exon_rows = parse_exon_coverage_tsv(args.exon_coverage)
    hsmetrics = parse_hsmetrics(args.hsmetrics)
    per_gene  = per_gene_rollup(exon_rows)

    # Mean of per-exon means is the headline coverage figure
    # (trusted because we compute it ourselves from the TSV, with the
    # patched mosdepth --flag 772 behavior).
    if exon_rows:
        mean_of_exon_means = sum(r["Mean_Coverage"] for r in exon_rows) / len(exon_rows)
    else:
        mean_of_exon_means = None

    chart_uri = render_per_gene_chart(
        per_gene,
        reference_coverage=mean_of_exon_means,
        reference_label="mean of exon means",
    )

    html = render_html(
        sample=args.sample,
        panel_name=args.panel_name,
        exon_rows=exon_rows,
        hsmetrics=hsmetrics,
        per_gene=per_gene,
        chart_data_uri=chart_uri,
        commit_sha=args.commit_sha,
        run_date=args.run_date,
        mean_of_exon_means=mean_of_exon_means,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote: {args.output}")
    print(f"  {len(exon_rows)} exons, {len(per_gene)} genes, "
          f"{sum(1 for r in exon_rows if r['Flag'] == 'LOW_COVERAGE')} low-cov")
    print(f"  Mean of exon means: "
          f"{mean_of_exon_means:.1f}x" if mean_of_exon_means else "  Mean: n/a")
    print(f"  HTML size: {args.output.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
