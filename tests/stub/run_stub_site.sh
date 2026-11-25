#!/usr/bin/env bash
# tests/stub/run_stub_site.sh -- can the pipeline be installed on a server that is neither gandalf
# nor clinical-23, without editing a tracked file? (MARKER PORTABLE_V1)
#
# Builds a throw-away "site" under a temporary directory: empty stand-ins for every reference file,
# two empty FASTQ pairs, and a site profile made from conf/site_template.config by setting
# site_root, exactly as a new installation would. Then:
#
#   1. resolves the configuration for `-profile site` with the Twist overlay and requires that no
#      parameter and no container setting points at the development host or at clinical-23, and
#      that the image is assigned to the processes that need it;
#   2. runs the whole workflow in stub mode (every process, no tool, no container, no data) for a
#      male and a female sample and requires that it completes, that the processes of the CNV stack
#      including the hmftools arm are in it, and that no task script or wrapper names a path of
#      another site;
#   3. requires the three launch mistakes that used to fail late or obscurely to stop at once with
#      a message that says what to do: no hmftools resource root, no panel overlay, a site profile
#      that does not exist;
#   4. requires a v1.0.x parameter file, which names the hmftools files one by one, to keep working;
#   5. resolves the two named site profiles and requires the values a run depends on to be the ones
#      of the release (gandalf: hmftools root and container runtime options unchanged).
#
#   bash tests/stub/run_stub_site.sh            about two minutes
#   bash tests/stub/run_stub_site.sh --keep     leave the temporary site in place and print its path
#
# Needs nextflow (the pinned 25.10.x) and java on PATH. Nothing outside the temporary directory is
# written; NXF_HOME is left as it is.
set -uo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
ROOT=$(mktemp -d "${TMPDIR:-/tmp}/tspipe_stub_site.XXXXXX")
[ "$KEEP" = 1 ] || trap 'rm -rf "$ROOT"' EXIT
OTHER_SITES='/goast|/home/hemat|patkarlab-clinical|/soft/apptainer'
fail=0
ok()   { echo "ok   $1"; }
bad()  { echo "FAIL $1"; [ -n "${2:-}" ] && echo "     $2"; fail=1; }
check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "got '$2', expected '$3'"; fi; }
nf() { nextflow "$@" 2>&1 | grep -v "^Picked up "; return "${PIPESTATUS[0]}"; }

# ---------------------------------------------------------------- the throw-away site
SITE=$ROOT/site
REF=$SITE/references
HMF=$REF/hmftools/hmf_pipeline_resources.38_v3.0.0--8
mkdir -p "$REF"/{hg38_broad,adapters,dbSNPGATK_hg38,vep_cache,annovar/humandb} "$SITE"/{images,vv_cache,fastq} \
         "$HMF"/dna/copy_number "$HMF"/dna/variants "$HMF"/common/ensembl_data
FA=$REF/hg38_broad/Homo_sapiens_assembly38.masked
for ext in .fasta .fasta.fai .fasta.alt .fasta.0123 .fasta.amb .fasta.ann .fasta.bwt.2bit.64 .fasta.pac .dict; do : > "$FA$ext"; done
: > "$REF/adapters/illumina_adapters.fa"
for v in Homo_sapiens_assembly38.dbsnp138 Mills_and_1000G_gold_standard.indels.hg38 af-only-gnomad.hg38; do
    : > "$REF/dbSNPGATK_hg38/$v.vcf.gz"; : > "$REF/dbSNPGATK_hg38/$v.vcf.gz.tbi"
done
: > "$HMF/dna/copy_number/AmberGermlineSites.38.tsv.gz"
: > "$HMF/dna/copy_number/GC_profile.1000bp.38.cnp"
: > "$HMF/dna/variants/KnownHotspots.somatic.38.vcf.gz"
echo "sample,fastq_1,fastq_2,sex" > "$SITE/samplesheet.csv"
for s in STUBM:male STUBF:female; do
    id=${s%%:*}
    : > "$SITE/fastq/${id}_R1.fastq.gz"; : > "$SITE/fastq/${id}_R2.fastq.gz"
    echo "$id,$SITE/fastq/${id}_R1.fastq.gz,$SITE/fastq/${id}_R2.fastq.gz,${s##*:}" >> "$SITE/samplesheet.csv"
done
# the site profile: the template with its one line changed
sed "s#/path/to/tspipe_site#$SITE#" "$REPO/conf/site_template.config" > "$SITE/site.config"
grep -q "site_root *= *'$SITE'" "$SITE/site.config" || bad "site_root line not found in conf/site_template.config"
# a stub run needs no container engine and must fit a small machine
cat > "$SITE/stub.config" <<'CFG'
params { max_cpus = 2; max_memory = '6.GB'; max_time = '1.h' }
singularity.enabled = false
docker.enabled      = false
executor { $local { cpus = 2; memory = '6 GB'; queueSize = 2 } }
CFG
export TSPIPE_SITE_CONFIG=$SITE/site.config
cd "$ROOT"

# ---------------------------------------------------------------- 1. resolved configuration
if nf -c "$REPO/conf/twist_apply.config" config -flat -profile site,singularity "$REPO" > "$ROOT/site.cfg"; then
    ok "1a configuration resolves for -profile site,singularity with the Twist overlay"
else
    bad "1a configuration does not resolve" "$(tail -3 "$ROOT/site.cfg")"
fi
check "1b no setting points at another site" "$(grep -cE "$OTHER_SITES" "$ROOT/site.cfg")" "0"
check "1c hmftools root comes from the site profile" \
      "$(grep -E '^params\.hmf_root ' "$ROOT/site.cfg" | cut -d"'" -f2)" "$HMF"
check "1d the image is assigned (containers.config applied without the site file including it)" \
      "$(grep -c "container = 'local/tspipe-host" "$ROOT/site.cfg" | awk '{print ($1 >= 6) ? "yes" : "no"}')" "yes"
check "1e blacklist is the checkout's validated file" \
      "$(grep -E '^params\.snv_blacklist ' "$ROOT/site.cfg" | cut -d"'" -f2)" "$REPO/references/blacklist_file.tsv"
check "1f in-image python for the annotation steps" \
      "$(grep -E '^params\.legacy_python_env ' "$ROOT/site.cfg" | cut -d"'" -f2)" "/opt/envs/targeted-seq"

# ---------------------------------------------------------------- 2. the whole workflow, stub mode
stub() {   # $1 = tag; further args: extra nextflow options (before `run`) then run options
    local tag=$1; shift
    nf "$@" > "$ROOT/$tag.log"
}
RUN_OPTS=(-profile site -stub-run --input "$SITE/samplesheet.csv" -ansi-log false)
if stub full -c "$REPO/conf/twist_apply.config" -c "$SITE/stub.config" run "$REPO" "${RUN_OPTS[@]}" \
        --outdir "$SITE/out" -w "$SITE/work"; then
    ok "2a stub run of the whole workflow completes ($(grep -c 'Submitted process' "$ROOT/full.log") tasks)"
else
    bad "2a stub run failed" "$(grep -E 'ERROR|Error|error' "$ROOT/full.log" | head -3)"
fi
for p in CNV_BAF_CNLOH CNV_CONSENSUS_MULTI CHROM_PAGES HMF_AMBER HMF_COBALT HMF_PURPLE PURECN DECON DASHBOARD RUN_BUNDLE; do
    n=$(grep -c "Submitted process > .*:$p (" "$ROOT/full.log")
    [ "$n" -ge 1 ] && ok "2b $p ran ($n)" || bad "2b $p did not run"
done
check "2c no task script or wrapper names a path of another site" \
      "$(grep -rlE "$OTHER_SITES" "$SITE/work" --include=.command.sh --include=.command.run 2>/dev/null | wc -l | tr -d ' ')" "0"
check "2d a report per sample and the run bundle are published" \
      "$(ls "$SITE"/out/STUBM/clinical/STUBM_report.html "$SITE"/out/STUBF/clinical/STUBF_report.html "$SITE"/out/*_reports.zip 2>/dev/null | wc -l | tr -d ' ')" "3"

# ---------------------------------------------------------------- 3. launch mistakes stop at once
grep -v "hmf_root " "$SITE/site.config" > "$SITE/site_nohmf.config"
TSPIPE_SITE_CONFIG=$SITE/site_nohmf.config stub nohmf -c "$REPO/conf/twist_apply.config" -c "$SITE/stub.config" \
    run "$REPO" "${RUN_OPTS[@]}" --outdir "$SITE/out_nohmf" -w "$SITE/work_nohmf"
check "3a no hmftools root: stops before any task" "$(grep -c 'Submitted process' "$ROOT/nohmf.log")" "0"
check "3b ... and says to set params.hmf_root" "$(grep -c 'Set params.hmf_root in the site profile' "$ROOT/nohmf.log")" "1"

stub nooverlay -c "$SITE/stub.config" run "$REPO" "${RUN_OPTS[@]}" --outdir "$SITE/out_nooverlay" -w "$SITE/work_nooverlay"
check "3c no panel overlay: stops before any task" "$(grep -c 'Submitted process' "$ROOT/nooverlay.log")" "0"
check "3d ... and names conf/twist_apply.config" "$(grep -c 'launch with `-c conf/twist_apply.config`' "$ROOT/nooverlay.log")" "1"

TSPIPE_SITE_CONFIG=$SITE/does_not_exist.config nf config -profile site "$REPO" > "$ROOT/nosite.log"
check "3e a site profile that does not exist is named in the error" "$(grep -c "does_not_exist.config" "$ROOT/nosite.log")" "1"

# ---------------------------------------------------------------- 4. a v1.0.x parameter file still works
cat > "$SITE/params_v10x.yaml" <<YAML
hmf_resources: "$HMF"
hmf_loci: "$HMF/dna/copy_number/AmberGermlineSites.38.tsv.gz"
hmf_gc_profile: "$HMF/dna/copy_number/GC_profile.1000bp.38.cnp"
hmf_ensembl_dir: "$HMF/common/ensembl_data"
hmf_hotspots: "$HMF/dna/variants/KnownHotspots.somatic.38.vcf.gz"
vv_cache_dir: "$SITE/vv_cache"
YAML
if TSPIPE_SITE_CONFIG=$SITE/site_nohmf.config stub paramsfile -c "$REPO/conf/twist_apply.config" -c "$SITE/stub.config" \
        run "$REPO" "${RUN_OPTS[@]}" -params-file "$SITE/params_v10x.yaml" --outdir "$SITE/out_pf" -w "$SITE/work_pf"; then
    ok "4  a parameter file naming the hmftools files one by one (v1.0.x) still drives a complete run"
else
    bad "4  run with a v1.0.x parameter file failed" "$(grep -E 'ERROR|Error' "$ROOT/paramsfile.log" | head -3)"
fi

# ---------------------------------------------------------------- 5. the two named site profiles
unset TSPIPE_SITE_CONFIG
nf -c "$REPO/conf/twist_apply.config" config -flat -profile gandalf,singularity "$REPO" > "$ROOT/gandalf.cfg"
check "5a gandalf: hmftools root as released" "$(grep -E '^params\.hmf_root ' "$ROOT/gandalf.cfg" | cut -d"'" -f2)" \
      "/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8"
check "5b gandalf: container runtime options as released" "$(grep -E '^singularity\.runOptions ' "$ROOT/gandalf.cfg" | cut -d"'" -f2)" \
      "-B /goast/hemat_data -B /home/hemat/programs"
check "5c gandalf: default output directory as released" "$(grep -E '^params\.outdir ' "$ROOT/gandalf.cfg" | cut -d"'" -f2)" \
      "/goast/hemat_data/nfcore_runs/default"
nf -c "$REPO/conf/twist_apply.config" config -flat -profile clinical23,singularity "$REPO" > "$ROOT/c23.cfg"
check "5d clinical-23: hmftools root on its own storage, without a parameter file" \
      "$(grep -E '^params\.hmf_root ' "$ROOT/c23.cfg" | cut -d"'" -f2)" \
      "/scratch/patkarlab-clinical/tspipe_release/refs/hmftools/hmf_pipeline_resources.38_v3.0.0--8"
check "5e clinical-23: no parameter points at the development host" \
      "$(grep -cE "^params\.[A-Za-z_]+ = '(/goast|/home/hemat)" "$ROOT/c23.cfg")" "0"

echo
[ "$KEEP" = 1 ] && echo "temporary site kept: $ROOT"
[ "$fail" = 0 ] && echo "stub site test passed" || { echo "stub site test FAILED"; exit 1; }
