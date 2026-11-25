#!/usr/bin/env bash
# tools/verify_install.sh -- check a host before running the frozen pipeline.
#
# Verifies: Nextflow and Java, the container runtime, every image named in
# docs/release/image_checksums.md5, and every reference the resolved profile points at (existence,
# size, and md5 against docs/release/reference_manifest.tsv where the manifest has one).
#
# Usage (from the repo root, on the target host):
#   bash tools/verify_install.sh -profile clinical23,singularity -c conf/twist_apply.config
#   bash tools/verify_install.sh -profile site,singularity -c conf/twist_apply.config     (conf/site.config)
# Any arguments are passed to `nextflow config`, so use the same profile and overlays as the run.
#
# Exit 0 when everything checks out, 1 otherwise. Nothing is written outside /tmp.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
MANIFEST=docs/release/reference_manifest.tsv
CHECKSUMS=docs/release/image_checksums.md5
fail=0
note() { printf "[%-4s] %s\n" "$1" "$2"; [ "$1" = "FAIL" ] && fail=1; return 0; }

echo "=== 1. toolchain"
nf=$(nextflow -version 2>/dev/null | grep -oE "version [0-9.]+" | awk '{print $2}')
[ -n "$nf" ] && note OK "nextflow $nf" || note FAIL "nextflow not found"
case "$nf" in 25.10.*) : ;; *) note WARN "the release was validated on Nextflow 25.10.4" ;; esac
jv=$(java -version 2>&1 | head -1)
[ -n "$jv" ] && note OK "$jv" || note FAIL "java not found"
# The container runtime is checked after the configuration is resolved (section 2): a site whose
# runtime is not on the default PATH says where it is in its profile's beforeScript, and that is
# the PATH a task will have. (PORTABLE_V1: this script used to add one site's apptainer path itself.)

echo "=== 2. resolved configuration"
CFG=/tmp/verify_cfg_$$.txt
# `nextflow -c <file> config ...`: -c is a global option and must precede the sub-command.
PRE=(); POST=(); PARAMS_FILE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -c) PRE+=(-c "$2"); shift 2 ;;
        -params-file) PARAMS_FILE="$2"; shift 2 ;;
        *)  POST+=("$1"); shift ;;
    esac
done
nextflow "${PRE[@]}" config -flat "${POST[@]}" . > "$CFG" 2>/tmp/verify_cfg_$$.err || { note FAIL "nextflow config failed: $(tail -1 /tmp/verify_cfg_$$.err)"; exit 1; }
# `nextflow config` has no -params-file (it is a `run` option), so apply the file here: a params
# file overrides both the profile and any -c overlay, which is how site paths are redirected.
if [ -n "$PARAMS_FILE" ]; then
    [ -f "$PARAMS_FILE" ] || { note FAIL "params file not found: $PARAMS_FILE"; exit 1; }
    n=0
    while IFS= read -r line; do
        case "$line" in ''|'#'*) continue ;; esac
        key=$(printf '%s' "${line%%:*}" | tr -d ' ')
        val=$(printf '%s' "${line#*:}" | sed 's/^ *//; s/ *$//; s/^"//; s/"$//')
        [ -n "$key" ] || continue
        grep -v "^params\.$key " "$CFG" > "$CFG.tmp" && mv "$CFG.tmp" "$CFG"
        echo "params.$key = '$val'" >> "$CFG"
        n=$((n+1))
    done < "$PARAMS_FILE"
    note OK "params file applied: $PARAMS_FILE ($n overrides)"
fi
CACHE=$(grep -E "^singularity.cacheDir" "$CFG" | head -1 | cut -d= -f2- | tr -d " '\"")
note OK "image cache: ${CACHE:-<unset>}"
# every reference path of the resolved configuration that still points at the development host
if [[ " ${POST[*]} " != *"gandalf"* ]]; then
    stray=$(grep -E "^params\.[A-Za-z_]+ = '(/goast|/home/hemat)" "$CFG" | cut -d' ' -f1 | sed 's/^params\.//' | tr '\n' ' ')
    [ -z "$stray" ] && note OK "no parameter points at the development host (/goast, /home/hemat)" \
        || note FAIL "parameters still pointing at the development host: $stray"
fi

echo "=== 2b. container runtime"
RT_DIR=$(grep -E "^process.beforeScript" "$CFG" | head -1 | grep -oE "PATH=[^:'\"]+" | head -1 | cut -d= -f2)
if [ -n "$RT_DIR" ]; then
    [ -d "$RT_DIR" ] && { export PATH="$RT_DIR:$PATH"; note OK "runtime directory from the profile's beforeScript: $RT_DIR"; } \
        || note FAIL "the profile's beforeScript adds $RT_DIR to PATH, which does not exist on this host"
fi
if command -v apptainer >/dev/null; then note OK "$(apptainer --version)"
elif command -v singularity >/dev/null; then note OK "$(singularity --version)"
else note FAIL "no apptainer/singularity on PATH"; fi
command -v squashfuse >/dev/null && note OK "squashfuse present (.sif can be mounted)" \
    || note WARN "no squashfuse here; compute nodes may also lack it - sandboxes (tools/make_sandboxes.sh) are the safe form"

echo "=== 3. images"
while read -r md5 name; do
    [ -n "${name:-}" ] || continue
    p="$CACHE/$name"
    if [ -d "$p" ]; then note OK "$name (sandbox)"
    elif [ -f "$p" ]; then
        got=$(md5sum "$p" | cut -d' ' -f1)
        [ "$got" = "$md5" ] && note OK "$name (sif, md5 match)" || note FAIL "$name md5 $got != $md5"
    else note WARN "$name absent (only needed if the run uses it)"; fi
done < "$CHECKSUMS"

echo "=== 4. references"
HMF_ROOT=$(grep -E "^params\.hmf_root " "$CFG" | head -1 | cut -d= -f2- | sed "s/^ *//; s/^'//; s/'$//")
[ "$HMF_ROOT" = "null" ] && HMF_ROOT=""
[ -z "$HMF_ROOT" ] && HMF_ROOT=$(grep -E "^params\.hmf_resources " "$CFG" | head -1 | cut -d= -f2- | sed "s/^ *//; s/^'//; s/'$//")
while IFS=$'\t' read -r param gpath type size md5; do
    [ "$param" = "param" ] && continue
    # vestigial on a containerised install: the modules call the in-image binaries
    case "$param" in legacy_root|legacy_python_env|filt3r_bin|filt3r_ref|getitd_path|vardict_bin) continue ;; esac
    val=$(grep -E "^params\.$param " "$CFG" | head -1 | cut -d= -f2- | sed "s/^ *//; s/^'//; s/'$//")
    if [ -z "$val" ] || [ "$val" = "null" ]; then
        # PORTABLE_V1: the hmftools reference files are found under the site's hmf_root by the workflow
        # (workflows/tspipe.nf) unless a parameter names one individually; same relative paths here.
        case "$param" in
            hmf_resources)   rel="" ;;
            hmf_loci)        rel="/dna/copy_number/AmberGermlineSites.38.tsv.gz" ;;
            hmf_gc_profile)  rel="/dna/copy_number/GC_profile.1000bp.38.cnp" ;;
            hmf_ensembl_dir) rel="/common/ensembl_data" ;;
            hmf_hotspots)    rel="/dna/variants/KnownHotspots.somatic.38.vcf.gz" ;;
            *)               rel="-" ;;
        esac
        if [ "$rel" != "-" ] && [ -n "$HMF_ROOT" ]; then val="$HMF_ROOT$rel"
        elif [ "$rel" != "-" ]; then note FAIL "params.hmf_root is not set: the site profile must say where the hmftools resource bundle is ($param)"; continue
        else note WARN "params.$param not set in this profile"; continue; fi
    fi
    case "$val" in
        /opt/*) note OK "$param -> $val (inside the image)"; continue ;;
        /*) : ;;
        *) continue ;;
    esac
    if [ "$type" = "DIR" ]; then
        [ -d "$val" ] && note OK "$param -> $val ($(ls "$val" | wc -l) entries)" || note FAIL "$param missing: $val"
    elif [ -f "$val" ]; then
        gsize=$(stat -c %s "$val")
        if [ -n "$md5" ]; then
            got=$(md5sum "$val" | cut -d' ' -f1)
            [ "$got" = "$md5" ] && note OK "$param md5 match" || note FAIL "$param md5 $got != $md5 ($val)"
        elif [ "$gsize" = "$size" ]; then note OK "$param size match"
        else note FAIL "$param size $gsize != $size ($val)"; fi
    else note FAIL "$param missing: $val"; fi
done < "$MANIFEST"

echo "=== 5. reference companions"
REF=$(grep -E "^params.reference " "$CFG" | head -1 | cut -d= -f2- | tr -d " '\"")
for ext in .fai .alt .0123 .bwt.2bit.64 .pac .ann .amb; do
    [ -f "${REF}${ext}" ] && note OK "$(basename "${REF}${ext}")" || note FAIL "missing $(basename "${REF}${ext}") beside the reference"
done
D=$(dirname "$REF"); [ -f "${REF%.fasta}.dict" ] && note OK "$(basename "${REF%.fasta}.dict")" || note FAIL "missing sequence dictionary"

echo "=== 6. writable locations"
for p in $(grep -E "^params.(outdir|vv_cache_dir) " "$CFG" | cut -d= -f2- | tr -d " '\""); do
    d=$p; [ -d "$d" ] || d=$(dirname "$p")
    [ -w "$d" ] && note OK "writable: $d" || note WARN "not writable: $d"
done
echo "=== 7. panel completeness"
PANEL=$(grep -E "^params.panel " "$CFG" | head -1 | cut -d= -f2- | tr -d " '\"")
ASSETS="$REPO/assets/${PANEL}"
if [ -d "$ASSETS" ] && [ -f "$REPO/tools/check_panel_completeness.py" ]; then
    CALLBED=$(grep -E "^params.bed " "$CFG" | head -1 | cut -d= -f2- | tr -d " '\"")
    if python3 "$REPO/tools/check_panel_completeness.py" \
           --assets "$ASSETS" --calling-bed "$CALLBED" --quiet; then
        note OK "panel completeness: every probe interval is callable"
    else
        note FAIL "panel completeness check failed (see lines above)"
    fi
else
    note WARN "panel completeness check skipped (no assets/${PANEL} or script)"
fi

rm -f "$CFG" /tmp/verify_cfg_$$.err
echo
[ "$fail" = 0 ] && echo "VERIFY PASSED" || echo "VERIFY FAILED (see FAIL lines above)"
exit $fail
