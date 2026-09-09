#!/usr/bin/env bash
# housekeeping_n10.sh -- register item N10 (2026-09-09). Dry-run by default; --apply executes.
#
# Reviewed against the 9 Sep survey. Nothing is deleted except .bak_* files that git does not
# track (every committed state is in history); scratch directories are MOVED out of the tree.
#
#  1. probes_ok_*.bed            -> assets/twist_myeloid/probes/ (provenance of spikein_regions.tsv), tracked
#  2. normals_twist.csv          -> pon_samplesheets/normals_twist.csv, tracked
#     pon_samplesheets/twist_males_24_fastq.csv, tools/verify_s3_archived.py  tracked
#  3. subworkflows/local/reporting.nf  git rm (stale; only .bak copies of tspipe.nf reference it)
#  4. qc/, references/backups/, run8_*.log  -> ${SCRATCH} (outside the repo)
#  5. *.bak_* files not tracked by git and not modified today: deleted (today's stay one more day)
#  6. nextflow clean -f for the two -preview sessions and the silly_bardeen stub session
#     (the live resume session abea2914 is never touched: cached tasks live in its earlier runs)
#
# After --apply: review `git status`, then commit (message suggested at the end).
set -euo pipefail

REPO=${N10_REPO:-/goast/hemat_data/nf-core-tspipe}
SCRATCH=${N10_SCRATCH:-/goast/hemat_data/twist_val/repo_scratch_$(date +%Y-%m-%d)}
TODAY=$(date +%Y-%m-%d)
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

cd "$REPO"
run() { if [[ $APPLY -eq 1 ]]; then echo "[do]   $*"; eval "$@"; else echo "[plan] $*"; fi; }

echo "== 1. probe BEDs -> assets/twist_myeloid/probes/"
run mkdir -p assets/twist_myeloid/probes
for f in probes_ok_*.bed; do
  [[ -f "$f" ]] && run mv "$f" "assets/twist_myeloid/probes/$f"
done
run git add assets/twist_myeloid/probes/

echo "== 2. samplesheets and the S3 check tool tracked"
[[ -f normals_twist.csv ]] && run mv normals_twist.csv pon_samplesheets/normals_twist.csv
run git add pon_samplesheets/normals_twist.csv pon_samplesheets/twist_males_24_fastq.csv tools/verify_s3_archived.py

echo "== 3. stale subworkflow"
[[ -f subworkflows/local/reporting.nf ]] && run git rm -q subworkflows/local/reporting.nf

echo "== 4. scratch out of the tree -> $SCRATCH"
run mkdir -p "$SCRATCH/run8_logs"
[[ -d qc ]] && run mv qc "$SCRATCH/qc"
[[ -d references/backups ]] && run mv references/backups "$SCRATCH/references_backups"
for f in run8_*.log; do [[ -f "$f" ]] && run mv "$f" "$SCRATCH/run8_logs/$f"; done

echo "== 5. untracked .bak_* files not modified today"
mapfile -t BAKS < <(find . -path ./work -prune -o -type f -name '*.bak_*' ! -newermt "$TODAY 00:00" -print | sed 's|^\./||')
n_del=0; n_keep=0
for f in "${BAKS[@]}"; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then n_keep=$((n_keep+1)); echo "[keep] tracked: $f"; continue; fi
  n_del=$((n_del+1))
  if [[ $APPLY -eq 1 ]]; then rm -f "$f"; fi
done
echo "[$([[ $APPLY -eq 1 ]] && echo do || echo plan)] delete $n_del untracked .bak_* files older than today ($n_keep tracked ones kept)"
echo "     today's $(find . -path ./work -prune -o -type f -name '*.bak_*' -newermt "$TODAY 00:00" -print | wc -l) .bak_* files stay until tomorrow's housekeeping"

echo "== 6. nextflow clean: preview and stub sessions only"
if command -v nextflow >/dev/null; then
  for r in distracted_bartik mighty_curran silly_bardeen; do
    run "nextflow clean -f -q $r 2>&1 | tail -1 || true"
  done
else
  echo "[skip] nextflow not on PATH"
fi

echo
echo "== git status after housekeeping"
git status --short | head -30
echo
echo "Suggested commit:"
echo "  git commit -q -m \"chore(n10): housekeeping - probe BEDs under assets/twist_myeloid/probes (spike-in provenance), normals and 24-male samplesheets and verify_s3_archived.py tracked, stale subworkflows/local/reporting.nf removed, scratch moved to $SCRATCH, old .bak files purged\""
