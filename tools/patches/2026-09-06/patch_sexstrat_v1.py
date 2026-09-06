#!/usr/bin/env python3
"""
patch_sexstrat_v1.py -- sex-stratified reference selection (MARKER SEXSTRAT_V1).

Wires the female-stratum assets into every consumer that today reads the
male file: GATK read-count PoN (GATK_CNV_DENOISE), CNVkit LOO summary and
noisy-bin blacklist (CNVKIT), LOO summary (CNV_ANNOTATE, CNV_CONSENSUS_MULTI).
Selection happens inside each process from meta.sex, with
params.cnv_sex_fallback (default 'male') for samples that are not
male/female. Panels without _female assets fall back to the male file at
the workflow level, so legacy panels keep today's behaviour.

Files (8): nextflow.config, conf/twist_apply.config, workflows/tspipe.nf,
subworkflows/local/cnv_calling.nf, subworkflows/local/gatk_cnv_calling.nf,
modules/local/{cnvkit,cnv_annotate,cnv_consensus_multi,gatk_cnv_denoise}.nf

Idempotent (per-file marker), dry run by default, --apply writes with
timestamped backups (.bak_sexstrat_<ts>). All edits are computed first;
nothing is written unless every required anchor matched.

Usage (repo root):
    python3 tools/patches/2026-09-06/patch_sexstrat_v1.py            # dry run
    python3 tools/patches/2026-09-06/patch_sexstrat_v1.py --apply
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER SEXSTRAT_V1"
TAG = "SEXSTRAT_V1"


def sub_once(text, pattern, repl, label, flags=re.M, required=True):
    """Replace exactly one match of pattern. Returns (text, note) or raises."""
    rx = re.compile(pattern, flags)
    hits = rx.findall(text)
    n = len(hits)
    if n == 0:
        if required:
            raise ValueError("anchor not found: %s" % label)
        return text, "[warn] optional anchor not found, skipped: %s" % label
    if n > 1:
        raise ValueError("anchor not unique (%d hits): %s" % (n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


# --------------------------------------------------------------------------
# nextflow.config
# --------------------------------------------------------------------------
def patch_nextflow_config(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)cnv_noisy_bins[ \t]*=[ \t]*null.*$",
        lambda m: m.group(0) + "\n"
        + "%s// %s: female-stratum LOO artefacts (male file used when a panel has none)\n" % (m.group("i"), MARKER)
        + "%scnv_loo_summary_female = null   // assets/${panel}/cnvkit_loo_summary_female.tsv fallback\n" % m.group("i")
        + "%scnv_noisy_bins_female  = null   // assets/${panel}/cnvkit_noisy_bins_female.bed fallback\n" % m.group("i")
        + "%scnv_sex_fallback       = 'male' // stratum for samples whose meta.sex is not male/female" % m.group("i"),
        "nextflow.config: params after cnv_noisy_bins")
    notes.append(n)
    return t, notes, 1


# --------------------------------------------------------------------------
# conf/twist_apply.config
# --------------------------------------------------------------------------
def patch_twist_apply(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)cnv_gatk_pon[ \t]*=[ \t]*\"(?P<p>[^\"]*)gatk_rc_pon_male\.hdf5\"[ \t]*$",
        lambda m: m.group(0) + "\n"
        + "%scnv_gatk_pon_female = \"%sgatk_rc_pon_female.hdf5\"   // %s" % (m.group("i"), m.group("p"), MARKER),
        "twist_apply.config: cnv_gatk_pon_female after cnv_gatk_pon")
    notes.append(n)
    return t, notes, 1


# --------------------------------------------------------------------------
# workflows/tspipe.nf
# --------------------------------------------------------------------------
TSPIPE_FEMALE_BLOCK = '''
{i}// {m}: female-stratum LOO artefacts. The male file is used when the panel
{i}// has no _female asset (legacy panels), with one log.warn. Selection by
{i}// meta.sex happens inside CNVKIT, CNV_ANNOTATE, CNV_CONSENSUS_MULTI and
{i}// GATK_CNV_DENOISE (params.cnv_sex_fallback for unknown/indeterminate).
{i}def sexstratFemale = {{ override, female_default, male_path ->
{i}    def f = override ?: female_default
{i}    if( file(f).exists() ) return file(f)
{i}    log.warn "[SEXSTRAT] ${{file(f).name}} not found for panel ${{params.panel}}; female stratum uses ${{file(male_path).name}}"
{i}    return file(male_path)
{i}}}
{i}ch_cnv_loo_summary_female = Channel.value( sexstratFemale(
{i}    params.cnv_loo_summary_female,
{i}    "${{projectDir}}/assets/${{params.panel}}/cnvkit_loo_summary_female.tsv",
{i}    params.cnv_loo_summary ?: "${{projectDir}}/assets/${{params.panel}}/cnvkit_loo_summary.tsv" ) )
{i}ch_cnv_noisy_bins_female  = Channel.value( sexstratFemale(
{i}    params.cnv_noisy_bins_female,
{i}    "${{projectDir}}/assets/${{params.panel}}/cnvkit_noisy_bins_female.bed",
{i}    params.cnv_noisy_bins ?: "${{projectDir}}/assets/${{params.panel}}/cnvkit_noisy_bins.bed" ) )'''


def patch_tspipe(t):
    notes = []
    # C1: female LOO channels after the noise-profile channel block
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)ch_cnv_noise_profile = Channel\.value\(file\(\n(?:.*\n)*?[ \t]*checkIfExists: true\)\)[ \t]*$",
        lambda m: m.group(0) + TSPIPE_FEMALE_BLOCK.format(i=m.group("i"), m=MARKER),
        "tspipe.nf: female LOO channels after ch_cnv_noise_profile")
    notes.append(n)
    # C2: CNV_CALLING call gets the two female channels at the end
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)ch_scatter_regions,\n(?P<j>[ \t]*)\)",
        lambda m: "%sch_scatter_regions,\n%sch_cnv_loo_summary_female,   // %s\n%sch_cnv_noisy_bins_female,    // %s\n%s)"
        % (m.group("i"), m.group("i"), TAG, m.group("i"), TAG, m.group("j")),
        "tspipe.nf: CNV_CALLING call")
    notes.append(n)
    # C3: female GATK PoN channel after ch_gatk_rc_pon
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)ch_gatk_rc_pon = Channel\.value\(file\(params\.cnv_gatk_pon, checkIfExists: true\)\)[ \t]*$",
        lambda m: m.group(0) + "\n"
        + "%s// %s: female GATK read-count PoN; male file when the panel has none.\n" % (m.group("i"), MARKER)
        + "%sdef gatk_pon_female = (params.containsKey('cnv_gatk_pon_female') && params.cnv_gatk_pon_female) ? params.cnv_gatk_pon_female : null\n" % m.group("i")
        + "%sch_gatk_rc_pon_female = Channel.value( sexstratFemale(gatk_pon_female,\n" % m.group("i")
        + "%s    \"${projectDir}/assets/${params.panel}/gatk_rc_pon_female.hdf5\", params.cnv_gatk_pon) )" % m.group("i"),
        "tspipe.nf: ch_gatk_rc_pon_female")
    notes.append(n)
    # C4: GATK_CNV_CALLING call gets the female PoN at the end
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)ch_baf_background,\n(?P<j>[ \t]*)\)",
        lambda m: "%sch_baf_background,\n%sch_gatk_rc_pon_female,   // %s\n%s)"
        % (m.group("i"), m.group("i"), TAG, m.group("j")),
        "tspipe.nf: GATK_CNV_CALLING call")
    notes.append(n)
    # C5: consensus call
    t, n = sub_once(
        t,
        r"CNV_CONSENSUS_MULTI\( ch_consensus_in, ch_cnv_loo_summary \)",
        "CNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female )   // %s" % TAG,
        "tspipe.nf: CNV_CONSENSUS_MULTI call")
    notes.append(n)
    return t, notes, 2


# --------------------------------------------------------------------------
# subworkflows/local/cnv_calling.nf
# --------------------------------------------------------------------------
def patch_cnv_calling(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)scatter_regions_ch[ \t]+// value path \(cnv_scatter_regions\.txt\)[ \t]*$",
        lambda m: m.group(0) + "\n"
        + "%sloo_summary_female_ch  // %s value path (cnvkit_loo_summary_female.tsv, or the male file)\n" % (m.group("i"), MARKER)
        + "%snoisy_bins_female_ch   // %s value path (cnvkit_noisy_bins_female.bed, or the male file)" % (m.group("i"), TAG),
        "cnv_calling.nf: take")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)noisy_bins_ch,\n(?P<j>[ \t]*)loo_summary_ch,\n(?P<k>[ \t]*)\)",
        lambda m: "%snoisy_bins_ch,\n%sloo_summary_ch,\n%snoisy_bins_female_ch,   // %s\n%sloo_summary_female_ch,  // %s\n%s)"
        % (m.group("i"), m.group("j"), m.group("j"), TAG, m.group("j"), TAG, m.group("k")),
        "cnv_calling.nf: CNVKIT call")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)clingen_ch,\n(?P<j>[ \t]*)bed_ch,\n(?P<k>[ \t]*)\)",
        lambda m: "%sclingen_ch,\n%sbed_ch,\n%sloo_summary_female_ch,  // %s\n%s)"
        % (m.group("i"), m.group("j"), m.group("j"), TAG, m.group("k")),
        "cnv_calling.nf: CNV_ANNOTATE call")
    notes.append(n)
    return t, notes, 1


# --------------------------------------------------------------------------
# subworkflows/local/gatk_cnv_calling.nf
# --------------------------------------------------------------------------
def patch_gatk_cnv_calling(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)baf_background[ \t]+// value path \(baf_background\.tsv\)[ \t]*$",
        lambda m: m.group(0) + "\n"
        + "%src_pon_female   // %s value path (gatk_rc_pon_female.hdf5, or the male file)" % (m.group("i"), MARKER),
        "gatk_cnv_calling.nf: take")
    notes.append(n)
    t, n = sub_once(
        t,
        r"GATK_CNV_DENOISE\( GATK_CNV_COLLECT_COUNTS\.out\.counts, rc_pon \)",
        "GATK_CNV_DENOISE( GATK_CNV_COLLECT_COUNTS.out.counts, rc_pon, rc_pon_female )   // %s" % TAG,
        "gatk_cnv_calling.nf: GATK_CNV_DENOISE call")
    notes.append(n)
    return t, notes, 1


# --------------------------------------------------------------------------
# modules
# --------------------------------------------------------------------------
STRATUM_DEF = "def stratum = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')"


def patch_cnvkit(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)path[ \t]+loo_summary[ \t]*$",
        lambda m: m.group(0) + "\n"
        + "%spath  noisy_bins_female,  stageAs: 'female_stratum/*'   // %s\n" % (m.group("i"), MARKER)
        + "%spath  loo_summary_female, stageAs: 'female_stratum/*'   // %s" % (m.group("i"), TAG),
        "cnvkit.nf: inputs")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)def sex[ \t]*=[ \t]*meta\.sex \?: 'unknown'\n[ \t]*def pon_use[ \t]*=[ \t]*\(sex == 'male'\) \? pon_male : pon_female[ \t]*$",
        lambda m: "%sdef sex       = meta.sex ?: 'unknown'\n" % m.group("i")
        + "%s// %s: PoN, LOO summary and noisy bins follow one stratum;\n" % (m.group("i"), TAG)
        + "%s// params.cnv_sex_fallback (default male) when sex is not male/female.\n" % m.group("i")
        + "%s%s\n" % (m.group("i"), STRATUM_DEF)
        + "%sdef pon_use   = (stratum == 'female') ? pon_female : pon_male\n" % m.group("i")
        + "%sdef noisy_use = (stratum == 'female') ? noisy_bins_female : noisy_bins\n" % m.group("i")
        + "%sdef loo_use   = (stratum == 'female') ? loo_summary_female : loo_summary" % m.group("i"),
        "cnvkit.nf: stratum selection")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)if \[ \"\$\{sex\}\" = \"unknown\" \]; then\n[ \t]*echo \"\[WARN\] meta\.sex=unknown for \$\{meta\.id\}; using female PoN as fallback\.\" >&2\n[ \t]*echo \"\[WARN\][^\n]*\" >&2\n[ \t]*fi[ \t]*$",
        lambda m: "%secho \"[SEXSTRAT] ${meta.id}: sex=${sex} stratum=${stratum} pon=${pon_use} loo=${loo_use} blacklist=${noisy_use}\"\n" % m.group("i")
        + "%sif [ \"${sex}\" != \"${stratum}\" ]; then\n" % m.group("i")
        + "%s    echo \"[WARN] meta.sex=${sex} for ${meta.id}; using the ${stratum} stratum (params.cnv_sex_fallback). chrX copy ratio is not interpretable.\" >&2\n" % m.group("i")
        + "%sfi" % m.group("i"),
        "cnvkit.nf: fallback warning")
    notes.append(n)
    t, n = sub_once(t, r"--blacklist \$\{noisy_bins\}", "--blacklist ${noisy_use}", "cnvkit.nf: --blacklist")
    notes.append(n)
    t, n = sub_once(t, r"--loo-summary \$\{loo_summary\}", "--loo-summary ${loo_use}", "cnvkit.nf: --loo-summary")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^ \*   meta\.sex == 'unknown' \(or unset\) -> pon_female \(with a warning;\n \*     chrX on a male sample run against a female PoN will show as\n \*     systematic ~-1 log2 loss, which is reviewable but not silent\)$",
        " *   meta.sex not male/female -> params.cnv_sex_fallback stratum (default\n"
        " *     male; %s) with a warning; chrX is not interpretable then.\n"
        " *   The LOO summary and noisy-bin blacklist follow the same stratum." % TAG,
        "cnvkit.nf: header comment", required=False)
    notes.append(n)
    return t, notes, 1


def patch_cnv_annotate(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)path[ \t]+bed[ \t]*$",
        lambda m: m.group(0) + "\n%spath  loo_summary_female, stageAs: 'female_stratum/*'   // %s" % (m.group("i"), MARKER),
        "cnv_annotate.nf: input")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)script:\n(?P<j>[ \t]*)\"\"\"\n(?P<k>[ \t]*)python3 \$\{projectDir\}/bin/cnv_annotate\.py",
        lambda m: "%sscript:\n%s// %s\n%s%s\n%sdef loo_use = (stratum == 'female') ? loo_summary_female : loo_summary\n%s\"\"\"\n%secho \"[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} loo=${loo_use}\"\n%spython3 ${projectDir}/bin/cnv_annotate.py"
        % (m.group("i"), m.group("j"), TAG, m.group("j"), STRATUM_DEF, m.group("j"), m.group("j"), m.group("k"), m.group("k")),
        "cnv_annotate.nf: script header")
    notes.append(n)
    t, n = sub_once(t, r"--loo-summary \$\{loo_summary\}", "--loo-summary ${loo_use}", "cnv_annotate.nf: --loo-summary")
    notes.append(n)
    return t, notes, 1


def patch_cnv_consensus_multi(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)path loo_summary[ \t]*$",
        lambda m: m.group(0) + "\n%spath loo_summary_female, stageAs: 'female_stratum/*'   // %s" % (m.group("i"), MARKER),
        "cnv_consensus_multi.nf: input")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)script:\n(?P<j>[ \t]*)\"\"\"\n(?P<k>[ \t]*)cnv_consensus_multi\.py",
        lambda m: "%sscript:\n%s// %s\n%s%s\n%sdef loo_use = (stratum == 'female') ? loo_summary_female : loo_summary\n%s\"\"\"\n%secho \"[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} loo=${loo_use}\"\n%scnv_consensus_multi.py"
        % (m.group("i"), m.group("j"), TAG, m.group("j"), STRATUM_DEF, m.group("j"), m.group("j"), m.group("k"), m.group("k")),
        "cnv_consensus_multi.nf: script header")
    notes.append(n)
    t, n = sub_once(t, r"--loo-summary \$\{loo_summary\}", "--loo-summary ${loo_use}", "cnv_consensus_multi.nf: --loo-summary")
    notes.append(n)
    return t, notes, 1


def patch_gatk_denoise(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)path rc_pon[ \t]*$",
        lambda m: m.group(0) + "\n%spath rc_pon_female, stageAs: 'female_stratum/*'   // %s" % (m.group("i"), MARKER),
        "gatk_cnv_denoise.nf: input")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)def xmx = task\.memory \? Math\.max\(4, task\.memory\.toGiga\(\) - 2\) : 12[ \t]*\n(?P<j>[ \t]*)\"\"\"\n(?P<k>[ \t]*)gatk --java-options",
        lambda m: "%sdef xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 12\n%s// %s\n%s%s\n%sdef pon_use = (stratum == 'female') ? rc_pon_female : rc_pon\n%s\"\"\"\n%secho \"[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} pon=${pon_use}\"\n%sgatk --java-options"
        % (m.group("i"), m.group("i"), TAG, m.group("i"), STRATUM_DEF, m.group("i"), m.group("j"), m.group("k"), m.group("k")),
        "gatk_cnv_denoise.nf: script header")
    notes.append(n)
    t, n = sub_once(t, r"--count-panel-of-normals \$\{rc_pon\}", "--count-panel-of-normals ${pon_use}", "gatk_cnv_denoise.nf: --count-panel-of-normals")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^ \* DenoiseReadCounts against the sex-matched read-count PoN$",
        " * DenoiseReadCounts against the sex-matched read-count PoN (%s:\n * male or female HDF5 chosen per sample from meta.sex)" % TAG,
        "gatk_cnv_denoise.nf: header comment", required=False)
    notes.append(n)
    return t, notes, 1


FILES = [
    ("nextflow.config",                          patch_nextflow_config),
    ("conf/twist_apply.config",                  patch_twist_apply),
    ("workflows/tspipe.nf",                      patch_tspipe),
    ("subworkflows/local/cnv_calling.nf",        patch_cnv_calling),
    ("subworkflows/local/gatk_cnv_calling.nf",   patch_gatk_cnv_calling),
    ("modules/local/cnvkit.nf",                  patch_cnvkit),
    ("modules/local/cnv_annotate.nf",            patch_cnv_annotate),
    ("modules/local/cnv_consensus_multi.nf",     patch_cnv_consensus_multi),
    ("modules/local/gatk_cnv_denoise.nf",        patch_gatk_denoise),
]


def brace_balance(text):
    return text.count("{") - text.count("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    planned = []   # (path, new_text)
    failed = False
    for rel, fn in FILES:
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found")
            failed = True
            continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER)
            continue
        try:
            new_text, notes, expected = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc)
            failed = True
            continue
        for n in notes:
            print("   %s" % n)
        n_markers = new_text.count(MARKER)
        b0, b1 = brace_balance(original), brace_balance(new_text)
        print("   [check] markers %d (expected %d); brace balance %d/%d" % (n_markers, expected, b0, b1))
        if n_markers != expected or b0 != b1:
            print("   [error] verification failed")
            failed = True
            continue
        planned.append((path, original, new_text))

    if failed:
        print("\n[error] one or more files failed; nothing written")
        sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do")
        sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned))
        print("---- new lines ----")
        for path, original, new_text in planned:
            old_set = set(original.splitlines())
            print("## %s" % os.path.relpath(path, args.root))
            for line in new_text.splitlines():
                if line not in old_set:
                    print("+ " + line)
        sys.exit(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_sexstrat_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
