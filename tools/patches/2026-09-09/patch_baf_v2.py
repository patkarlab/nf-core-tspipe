#!/usr/bin/env python3
"""BAF_V2 -- genome-wide per-arm BAF / cnLOH detector (C2 on the register).

Run from the nf-core-tspipe repo root with baf_cnloh_detect_v2.py in the same directory as this
patcher. Dry-run by default; --apply writes. All-or-nothing; .bak_BAF_V2_<timestamp> backups.

bin/baf_cnloh_detect.py          replaced by the V2 detector (V1 kept as the .bak): every arm with
                                 informative background sites is evaluated; verdict per arm
                                 NEUTRAL / DEL / CNLOH / GAIN / IMBALANCE / INDETERMINATE; the noise
                                 floor comes from the sample's other arms (the cohort MAD is trimodal
                                 off 17p and unusable); cohort-median bias correction only at
                                 het-like sites. Outputs <sample>.baf.{summary,sites}.tsv/.png.
modules/local/cnv_baf_cnloh.nf   outputs renamed baf17p -> baf; --cr-gain ${params.baf_cr_gain}.
conf/twist_apply.config          baf_cr_gain = 0.15.
bin/cnv_consensus_multi.py       B arm per gene from the arm row overlapping the gene (V1 single-row
                                 format still accepted); b_call GAIN now possible; allelic_state
                                 '17p:CNLOH f=0.41'; payload gains baf_arms (baf17p kept as the 17p row).
bin/dashboard_builder/parsers/cnv_v2.py + templates/sample_report.html.j2
                                 "BAF by chromosome arm" table on the CNV tab; column key updated.

Resume cost: CNV_BAF_CNLOH (8) -> CNV_CONSENSUS_MULTI, EXON_PLOTS, CHROM_PAGES, ORGANIZE_OUTPUT,
DASHBOARD, REPORT_BUNDLE (~40 tasks).
"""
import argparse
import os
import shutil
import sys
import time

TAG = "BAF_V2"
STAMP = time.strftime("%Y%m%d_%H%M%S")
HERE = os.path.dirname(os.path.abspath(__file__))


class PatchError(Exception):
    pass


def read(path):
    if not os.path.isfile(path):
        raise PatchError("missing file: %s" % path)
    with open(path) as f:
        return f.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


# ---------------------------------------------------------------------------
def patch_module(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        " * modules/local/cnv_baf_cnloh.nf  (BAF_V1)\n *\n * 17p BAF-shift / cnLOH detector.",
        " * modules/local/cnv_baf_cnloh.nf  (BAF_V1 17p; BAF_V2 genome-wide per arm, 2026-09-09)\n *\n * Per-arm BAF-shift / cnLOH / allelic-imbalance detector. V1 text follows for the method.",
        "module header")
    text = replace_once(
        text,
        '        tuple val(meta), path("${meta.id}.baf17p.summary.tsv"), emit: summary\n'
        '        tuple val(meta), path("${meta.id}.baf17p.sites.tsv"),   emit: sites\n'
        '        tuple val(meta), path("${meta.id}.baf17p.png"),         emit: plot, optional: true\n',
        '        tuple val(meta), path("${meta.id}.baf.summary.tsv"), emit: summary   // BAF_V2: one row per arm\n'
        '        tuple val(meta), path("${meta.id}.baf.sites.tsv"),   emit: sites\n'
        '        tuple val(meta), path("${meta.id}.baf.png"),         emit: plot, optional: true\n',
        "module outputs")
    text = replace_once(
        text,
        '        touch ${meta.id}.baf17p.summary.tsv ${meta.id}.baf17p.sites.tsv ${meta.id}.baf17p.png\n',
        '        touch ${meta.id}.baf.summary.tsv ${meta.id}.baf.sites.tsv ${meta.id}.baf.png\n',
        "module stub")
    text = replace_once(
        text,
        '            --cr-del ${params.baf_cr_del} \\\\\n'
        '            --out-prefix ${meta.id}.baf17p\n',
        '            --cr-del ${params.baf_cr_del} \\\\\n'
        '            --cr-gain ${params.baf_cr_gain} \\\\\n'
        '            --out-prefix ${meta.id}.baf\n',
        "module script")
    return text, "patch"


def patch_config(text):
    if TAG in text:
        return text, "skip"
    return replace_once(
        text,
        "    baf_cr_del         = -0.15\n",
        "    baf_cr_del         = -0.15\n"
        "    baf_cr_gain        = 0.15    // BAF_V2: arm log2 copy-ratio median at or above this with a BAF shift -> GAIN\n",
        "config baf_cr_gain"), "patch"


# ---------------------------------------------------------------------------
CMX_READ_OLD = '''    # ---- BAF summary
    baf_hdr, baf_rows = read_tsv(args.baf_summary, comment="#")
    baf = baf_rows[0] if baf_rows else {}
    baf_region = baf.get("region", "chr17:0-0")
    m = re.match(r"(chr\\w+):(\\d+)-(\\d+)", baf_region)
    baf_chrom, baf_lo, baf_hi = (m.group(1), int(m.group(2)), int(m.group(3))) \\
        if m else ("chr17", 0, 0)
    baf_verdict = baf.get("verdict", "NA")
'''
CMX_READ_NEW = '''    # ---- BAF summary (BAF_V2: one row per chromosome arm; the V1 single-row 17p file is read the same way)
    baf_hdr, baf_rows = read_tsv(args.baf_summary, comment="#")
    baf_arms = []
    for r in baf_rows:
        m = re.match(r"(chr\\w+):(\\d+)-(\\d+)", r.get("region", ""))
        if m:
            baf_arms.append((m.group(1), int(m.group(2)), int(m.group(3)), r))
    baf = next((r for c, lo, hi, r in baf_arms if r.get("arm") == "17p"), baf_rows[0] if baf_rows else {})

    def baf_for_gene(chrom, start, end):
        best = None
        for c, lo, hi, r in baf_arms:
            if c != chrom:
                continue
            o = overlap(start, end, lo, hi)
            if o > 0 and (best is None or o > best[0]):
                best = (o, r)
        return best[1] if best else None
    print("[ok] BAF arm B: %d arm row(s); calls: %s" % (
        len(baf_arms), ", ".join("%s %s" % (r.get("arm"), r.get("verdict")) for _, _, _, r in baf_arms
                                 if r.get("verdict") not in ("NEUTRAL", "INDETERMINATE", None)) or "none"))
'''
CMX_GENE_OLD = '''        in_baf_region = g["chrom"] == baf_chrom and overlap(
            g["start"], g["end"], baf_lo, baf_hi) > 0
        b_call = "NA"
        if in_baf_region:
            b_call = {"DEL_17P": "LOSS", "CNLOH_17P": "CNLOH",
                      "NEUTRAL": "NEUTRAL"}.get(baf_verdict, "NA")
        allelic = baf_verdict if in_baf_region else "NA"
'''
CMX_GENE_NEW = '''        br = baf_for_gene(g["chrom"], g["start"], g["end"])   # BAF_V2: the arm row overlapping the gene
        bv = br.get("verdict", "NA") if br else "NA"
        b_low = bool(br) and br.get("confidence", "") == "LOW"   # BAF_V2: a LOW-confidence arm casts no B vote
        b_call = {"DEL_17P": "LOSS", "CNLOH_17P": "CNLOH", "DEL": "LOSS", "CNLOH": "CNLOH",
                  "GAIN": "GAIN", "NEUTRAL": "NEUTRAL"}.get(bv, "NA")
        if b_low:
            b_call = "NA"
        if br is None:
            allelic = "NA"
        elif bv == "INDETERMINATE":
            allelic = "%s:INDETERMINATE (n_het %s)" % (br.get("arm", "?"), br.get("n_het", "?"))
        elif bv in ("NEUTRAL", "NA"):
            allelic = "%s:%s" % (br.get("arm", "?"), bv)
        else:
            allelic = "%s:%s%s f=%s%s" % (br.get("arm", "?"), bv, "?" if b_low else "", br.get("f_estimate", "NA"),
                                          " (low confidence, no vote)" if b_low else "")
'''
CMX_PAYLOAD_OLD = '''        "baf17p": baf,\n'''
CMX_PAYLOAD_NEW = '''        "baf17p": baf,
        "baf_arms": [r for _, _, _, r in baf_arms],   # BAF_V2
'''
CMX_DOC_OLD = '''    B  BAF       -- sample-level 17p verdict (BAF_V1): genes inside the
                    17p test region get b_call LOSS for DEL_17P, CNLOH for
                    CNLOH_17P; allelic_state carries the verdict text.
'''
CMX_DOC_NEW = '''    B  BAF       -- per-arm verdict (BAF_V2; V1 was 17p only): a gene takes
                    the verdict of the chromosome arm it lies on -- b_call LOSS
                    for DEL, CNLOH for CNLOH, GAIN for GAIN; allelic_state carries
                    '<arm>:<verdict> f=<clonal fraction>'.
'''


def patch_cmx(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, CMX_DOC_OLD, CMX_DOC_NEW, "cmx docstring")
    text = replace_once(text, CMX_READ_OLD, CMX_READ_NEW, "cmx BAF read")
    text = replace_once(text, CMX_GENE_OLD, CMX_GENE_NEW, "cmx per-gene B")
    text = replace_once(text, CMX_PAYLOAD_OLD, CMX_PAYLOAD_NEW, "cmx payload")
    return text, "patch"


# ---------------------------------------------------------------------------
PARSER_OLD = '''    # ---- sex check ----
    sx = v2 / "sex_check" / ("%s.sex_check.tsv" % sample)
'''
PARSER_NEW = '''    # ---- BAF by arm (BAF_V2) ----
    for cand in (v2 / ("%s.baf.summary.tsv" % sample), v2 / "baf" / ("%s.baf.summary.tsv" % sample)):
        if cand.exists():
            rows = _read_tsv(cand)
            if rows:
                out["baf_arms"] = [{"arm": r.get("arm", ""), "n_het": r.get("n_het", ""), "f": r.get("f_estimate", ""),
                                    "cr": r.get("cr_median_log2", ""), "verdict": r.get("verdict", ""),
                                    "confidence": r.get("confidence", ""), "scope": r.get("scope", "")} for r in rows]
                out["baf_calls"] = [r for r in out["baf_arms"] if r["verdict"] not in ("NEUTRAL", "INDETERMINATE", "") and r["confidence"] == "HIGH"]
            break

    # ---- sex check ----
    sx = v2 / "sex_check" / ("%s.sex_check.tsv" % sample)
'''

TPL_KEY_OLD = '''                <tr><td class="text-nowrap"><code>b_call</code></td><td>B = B-allele frequency / cnLOH (17p region in the current version): LOSS, CNLOH or NEUTRAL</td></tr>
'''
TPL_KEY_NEW = '''                <tr><td class="text-nowrap"><code>b_call</code></td><td>B = B-allele frequency per chromosome arm (BAF_V2): LOSS, CNLOH, GAIN or NEUTRAL from the arm the gene lies on; <code>allelic_state</code> gives arm, verdict and clonal fraction</td></tr>
'''
TPL_TABLE_ANCHOR = '''          {{ macros.render_datatable('cnv-consensus-table', ctx.cnv.consensus_table.columns, ctx.cnv.consensus_table.rows) }}
'''
TPL_TABLE_NEW = TPL_TABLE_ANCHOR + '''
          {# BAF_V2: per-arm allelic state #}
          {% if ctx.cnv.baf_arms %}
          <h6 class="mt-4">BAF by chromosome arm
            {% if ctx.cnv.baf_calls %}<span class="badge bg-warning text-dark ms-1">{{ ctx.cnv.baf_calls|length }} arm(s) with a call</span>
            {% else %}<span class="badge bg-success ms-1">all arms balanced</span>{% endif %}
          </h6>
          <p class="text-muted small mb-2">Mirrored B-allele deviation over the sample's heterozygous catalog sites, per arm; the noise floor is the sample's own balanced arms. DEL / GAIN use the arm's denoised copy ratio; CNLOH is a shift at neutral copy number; INDETERMINATE means too few heterozygous sites (acrocentric p arms, chrX in males). A call marked ? is LOW confidence (fewer than 20 heterozygous sites or a deviation under 1.5 x the noise floor) and casts no vote in the consensus.</p>
          <div class="table-responsive" style="max-width: 900px;">
            <table class="table table-sm table-striped small mb-0">
              <thead class="table-light"><tr><th>Arm</th><th>Het sites</th><th>Clonal fraction</th><th>Copy ratio (log2)</th><th>Verdict</th><th>Confidence</th><th>Scope</th></tr></thead>
              <tbody>
              {% for a in ctx.cnv.baf_arms %}
                <tr{% if a.verdict in ('DEL','CNLOH','GAIN','IMBALANCE') and a.confidence == 'HIGH' %} class="table-warning"{% endif %}>
                  <td>{{ a.arm }}</td><td>{{ a.n_het }}</td><td>{{ a.f }}</td><td>{{ a.cr }}</td>
                  <td><strong>{{ a.verdict }}{% if a.confidence == 'LOW' %}?{% endif %}</strong></td><td>{{ a.confidence }}</td><td>{{ a.scope }}</td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
          {% endif %}
'''


def patch_parser(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, PARSER_OLD, PARSER_NEW, "cnv_v2 parser"), "patch"


def patch_template(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, TPL_KEY_OLD, TPL_KEY_NEW, "template column key")
    text = replace_once(text, TPL_TABLE_ANCHOR, TPL_TABLE_NEW, "template arm table")
    return text, "patch"


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    det_src = os.path.join(HERE, "baf_cnloh_detect_v2.py")
    if not os.path.isfile(det_src):
        print("[error] %s not found next to the patcher" % det_src); sys.exit(2)
    targets = [
        ("modules/local/cnv_baf_cnloh.nf", patch_module),
        ("conf/twist_apply.config", patch_config),
        ("bin/cnv_consensus_multi.py", patch_cmx),
        ("bin/dashboard_builder/parsers/cnv_v2.py", patch_parser),
        ("bin/dashboard_builder/templates/sample_report.html.j2", patch_template),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
        det = "bin/baf_cnloh_detect.py"
        cur = read(det)
        plan.append((det, read(det_src), "skip" if "BAF_V2" in cur else "replace"))
    except PatchError as e:
        print("[error] %s\n[error] nothing written" % e); sys.exit(1)
    for path, _, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write"); return
    for path, new, status in plan:
        if status == "skip":
            continue
        bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
        shutil.copy2(path, bak); print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
