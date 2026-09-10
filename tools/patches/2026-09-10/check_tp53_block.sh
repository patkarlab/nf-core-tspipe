#!/usr/bin/env bash
# TP53_OBS_V1 offline check. Run from the repo root on gandalf AFTER the patcher and the two file copies.
#
# Builds a scratch dashboard view (symlinks, no BAM copies) holding
#   26CGH1250-TwistMyVal  as published (17p GAIN, no TP53 variant -> "No reportable TP53 variant")
#   26CGH60-TwistMyVal    copy of the clinical table with two synthetic TP53 rows appended
#                         (a PASS p.Arg175His at 38.8 % and a LowQual p.Arg248Gln at 4.8 %),
#                         diploid 17 -> exercises the variant half of the block
# renders it with the exact interpreter the last DASHBOARD task used, prints the card as text
# and zips the two reports (+ assets/) into ~/inbox/from_claude/ for viewing.
# Nothing under the run outdir is touched.
set -euo pipefail

R=${RUN8:-/goast/hemat_data/twist_val/tspipe_run8}
REPO=$(pwd)
STAMP=$(date +%Y%m%d_%H%M)
SCR=${SCRATCH_BASE:-/goast/hemat_data/twist_val}/tp53_check_${STAMP}
VIEW=$SCR/dashboard_view
REAL=26CGH1250-TwistMyVal
SYN=26CGH60-TwistMyVal

[ -f bin/dashboard_builder/parsers/tp53.py ] || { echo "parsers/tp53.py missing"; exit 2; }
[ -f assets/twist_myeloid/tp53_interpretation_rules.tsv ] || { echo "rules asset missing"; exit 2; }
grep -q TP53_OBS_V1 bin/dashboard_builder/build.py || { echo "build.py not patched"; exit 2; }

# interpreter exactly as the last DASHBOARD task used it (override with PY=/path/to/python)
PY=${PY:-}
if [ -z "$PY" ]; then
    LAST=$(ls -td work/*/*/dashboard_view 2>/dev/null | head -1 || true)
    if [ -n "$LAST" ] && [ -f "$(dirname "$LAST")/.command.sh" ]; then
        PY=$(grep -m1 'build.py' "$(dirname "$LAST")/.command.sh" | awk '{print $1}')
    elif [ -f nextflow.config ]; then
        PY=$(grep -m1 -oE 'legacy_python_env *= *"[^"]+"' nextflow.config | sed -E 's/.*"([^"]+)"/\1/')/bin/python
    fi
fi
[ -n "$PY" ] && [ -x "$PY" ] || { echo "cannot locate the dashboard python (got '$PY'); re-run as PY=/path/to/python bash $0"; exit 2; }
echo "python: $PY  ($($PY --version 2>&1))"
KL=assets/twist_myeloid/known_low_exons.tsv;  [ -f $KL ] && KL_ARG="--known-low-exons $REPO/$KL" || KL_ARG=""
SP=assets/twist_myeloid/spikein_regions.tsv;  [ -f $SP ] && SP_ARG="--spikein-regions $REPO/$SP" || SP_ARG=""

stage () {   # stage <sample>: symlink every clinical/ entry, copy the IGV report (builder patches it in place)
    local s=$1 src=$R/$1/clinical dst=$VIEW/$1/clinical
    mkdir -p "$dst"
    for e in "$src"/*; do
        n=$(basename "$e")
        if [ "$n" = "${s}_igv_report.html" ]; then cp -L "$e" "$dst/$n"; else ln -sfn "$(readlink -f "$e")" "$dst/$n"; fi
    done
}
mkdir -p "$VIEW"
stage $REAL
stage $SYN

# synthetic TP53 rows on the copy of 26CGH60's clinical table (replaces the symlink with a real file)
T=$VIEW/$SYN/clinical/$SYN.somaticseq.clinical.final.tsv
rm -f "$T"; cp "$R/$SYN/clinical/$SYN.somaticseq.clinical.final.tsv" "$T"
$PY - "$T" <<'EOF'
import csv, sys
p = sys.argv[1]
with open(p) as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))
cols = list(rows[0].keys())
base = dict(rows[0])
def mk(**kw):
    r = dict((c, "") for c in cols); r.update(base); r.update(kw); return r
common = dict(Gene="TP53", Chr="chr17", Consequence="missense_variant", Filter="PASS",
              Variant_Class="nonsynonymous", MNV_Note="", Dedup_Note="", Blacklist_Reason="", Blacklist_Date="",
              HGVS_ITD="", Confirmed_by_FLT3_ITD_ensemble="")
r1 = mk(Start="7675088", End="7675088", Ref="C", Alt="T",
        HGVSc="ENST00000269305.9:c.524G>A", HGVSp="ENSP00000269305.4:p.Arg175His", HGVSg="chr17:g.7675088C>T",
        VV_HGVSc="NM_000546.6:c.524G>A", VV_HGVSp="NP_000537.3:p.(Arg175His)", VV_Transcript="NM_000546.6", VV_Exon="5",
        CAVA_HGVSc="c.524G>A", CAVA_HGVSp="p.Arg175His", CAVA_Transcript="NM_000546.6",
        VariantCaller_Count="6", Callers="Mutect2,VarScan,VarDict,Strelka,FreeBayes,Platypus",
        REF_COUNT="612", ALT_COUNT="388", VAF_pct="38.8", SomaticSeq_Verdict="PASS",
        COSMIC_ID="COSV52661038", ClinVar="Pathogenic", OncoVI_Classification="Oncogenic", OncoVI_Score="12", **common)
r2 = mk(Start="7674220", End="7674220", Ref="C", Alt="T",
        HGVSc="ENST00000269305.9:c.743G>A", HGVSp="ENSP00000269305.4:p.Arg248Gln", HGVSg="chr17:g.7674220C>T",
        VV_HGVSc="", VV_HGVSp="", VV_Transcript="", VV_Exon="",
        CAVA_HGVSc="c.743G>A", CAVA_HGVSp="p.Arg248Gln", CAVA_Transcript="NM_000546.6",
        VariantCaller_Count="2", Callers="VarDict,FreeBayes",
        REF_COUNT="900", ALT_COUNT="45", VAF_pct="4.8", SomaticSeq_Verdict="LowQual",
        COSMIC_ID="", ClinVar="", OncoVI_Classification="Likely oncogenic", OncoVI_Score="8", **common)
rows += [r1, r2]
with open(p, "w") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
    w.writeheader(); w.writerows(rows)
print("synthetic table rows:", len(rows), "(2 TP53 rows appended)")
EOF

# render (same flags as the module, no external annotation)
LOG=$SCR/build.log
$PY bin/dashboard_builder/build.py "$VIEW" --subdir clinical \
    --no-annotate-genebe --no-annotate-mobidetails \
    $KL_ARG $SP_ARG \
    --tp53-rules "$REPO/assets/twist_myeloid/tp53_interpretation_rules.tsv" > "$LOG" 2>&1 \
    || { echo "builder failed, see $LOG"; tail -30 "$LOG"; exit 1; }
grep -E "WARNING|ERROR|Wrote" "$LOG" | grep -v "existing_dashboard" || true

# the card and the Reporting line as plain text
$PY - "$VIEW" $REAL $SYN <<'EOF'
import re, html, sys
view = sys.argv[1]
for s in sys.argv[2:]:
    t = open("%s/%s/clinical/%s_report.html" % (view, s, s)).read()
    for a, b, lab in (('id="tp53-observation-card"', 'id="cnv-subtabs"', "CARD"),
                      ('id="reporting-tp53-line"', 'id="reporting-empty"', "REPORTING LINE")):
        i, j = t.index(a), t.index(b)
        txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[i:j])))
        print("== %s %s\n%s\n" % (s, lab, txt[:1500]))
EOF

mkdir -p ~/inbox/from_claude
( cd "$VIEW" && zip -qr ~/inbox/from_claude/tp53_check_${STAMP}.zip assets $REAL/clinical/${REAL}_report.html $SYN/clinical/${SYN}_report.html )
echo "review zip: ~/inbox/from_claude/tp53_check_${STAMP}.zip   (scratch view: $VIEW; remove with rm -rf $SCR when done)"
