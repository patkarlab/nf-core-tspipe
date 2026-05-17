#!/usr/bin/env python3
"""
apply_annotation_wiring.py

Wires the ANNOTATION subworkflow into the main tspipe.nf and fixes
several latent bugs in modules/local/variant_filter.nf along the way.

Background: VEP_ANNOTATE landed in commit 5cf6df6 but ANNOTATION(...)
in workflows/tspipe.nf is commented out, so VEP_ANNOTATE was not
exercised. Uncommenting ANNOTATION surfaced that the existing
variant_filter.nf is latently broken: it passes flags (--input,
--filtered, --clinical) that bin/variant_filter.py does not accept,
and declares outputs (.filtered.tsv, .clinical.tsv) that don't match
what the script actually writes (.somaticseq.filtered.tsv,
.somaticseq.clinical.tsv). The script discovers its input by
convention from --outdir, not via a flag. It also auto-merges
U2AF1 rescue results if a file named {sample}_u2af1_rescue.tsv is
present in the same dir.

This patch:

1. modules/local/variant_filter.nf -- full rewrite to match the
   script's real CLI (-s, -o, --blacklist), correct the output
   declarations, and add u2af1_tsv as a new input so the U2AF1
   rescue TSV gets staged into the work dir where variant_filter.py
   picks it up.

2. subworkflows/local/annotation.nf -- add u2af1_tsv_ch as the third
   take: parameter, join it with VEP_ANNOTATE.out.tsv before passing
   to VARIANT_FILTER.

3. workflows/tspipe.nf -- uncomment the ANNOTATION(...) call with
   its 5-channel signature.

The bin/variant_filter.py script is NOT modified. Its filename-
discovery-by-convention is an anti-pattern but rewriting it to take
proper --input/--u2af1 flags would drift from production and risk
breaking the tightly-coupled U2AF1 merge logic.
"""
import shutil
import sys
from pathlib import Path
from datetime import datetime

TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# --- New content for modules/local/variant_filter.nf -----------------------
#
# Full rewrite. Compared to the prior body:
# - input now takes tuple (meta, annotated_tsv, u2af1_tsv) instead of
#   tuple (meta, annotated_tsv)
# - script: block symlinks annotated_tsv to the filename the script
#   expects; U2AF1 TSV already arrives with the correct name from
#   U2AF1_RESCUE
# - CLI flags match what bin/variant_filter.py --help actually shows
# - output filenames now match what the script writes
# - conda directive trimmed (pysam was declared but not actually used
#   by variant_filter.py; only pandas + numpy are imported)
VARIANT_FILTER_NEW_CONTENT = '''/*
 * modules/local/variant_filter.nf
 *
 * Apply quality/region/blacklist filters to annotated variants and
 * merge in U2AF1 rescue hits. Mirrors production scripts/14_variant_filter.py.
 *
 * Filter precedence (priority 0 wins):
 *     BLACKLIST -> LowVAF / LowDepth / OffTarget / etc.
 *
 * BLACKLIST rows stay in filtered.tsv but are excluded from clinical.tsv.
 *
 * The wrapped bin/variant_filter.py discovers its inputs by convention
 * from --outdir, looking for ${meta.id}.somaticseq.annotated.tsv and
 * (optionally) ${meta.id}_u2af1_rescue.tsv. We symlink the annotated
 * TSV to the expected name; the U2AF1 TSV already arrives with the
 * right filename from U2AF1_RESCUE.
 */

process VARIANT_FILTER {
    tag        "${meta.id}"
    label      'process_low'

    conda      'conda-forge::pandas=2.1.4'

    input:
        tuple val(meta), path(annotated_tsv), path(u2af1_tsv)
        path  blacklist     // path or empty list

    output:
        tuple val(meta), path("${meta.id}.somaticseq.filtered.tsv"), emit: filtered
        tuple val(meta), path("${meta.id}.somaticseq.clinical.tsv"), emit: clinical
        path  "versions.yml",                                         emit: versions

    stub:
        // nf-core stub blocks v1
        """
        touch ${meta.id}.somaticseq.filtered.tsv ${meta.id}.somaticseq.clinical.tsv versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def bl_arg = blacklist ? "--blacklist ${blacklist}" : ''
        """
        # Rename VEP_ANNOTATE output to the filename variant_filter.py expects.
        # ln -sf is idempotent across retries in the same work dir.
        ln -sf ${annotated_tsv} ${meta.id}.somaticseq.annotated.tsv

        variant_filter.py \\\\
            --sample ${meta.id} \\\\
            --outdir . \\\\
            ${bl_arg}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \\$(python --version 2>&1 | sed 's/Python //')
            pandas: \\$(python -c "import pandas; print(pandas.__version__)")
        END_VERSIONS
        """
}
'''


# Each (path, list-of-replacements) pair. The variant_filter.nf rewrite
# is handled via Path.write_text() outside this table; the entries here
# are surgical string replacements only.
PATCHES = {
    Path("subworkflows/local/annotation.nf"): [
        # Replacement 1: extend the take: block with u2af1_tsv_ch as
        # parameter 3 (matching the commented-out call's channel order
        # in tspipe.nf).
        (
            "    take:\n"
            "        somaticseq_vcf_ch       // [meta, vcf]\n"
            "        flt3_consensus_tsv_ch   // [meta, tsv]\n"
            "        blacklist_ch            // path or []\n"
            "        reference_ch",
            "    take:\n"
            "        somaticseq_vcf_ch       // [meta, vcf]\n"
            "        flt3_consensus_tsv_ch   // [meta, tsv]\n"
            "        u2af1_tsv_ch            // [meta, tsv] (from U2AF1_RESCUE)\n"
            "        blacklist_ch            // path or []\n"
            "        reference_ch",
        ),
        # Replacement 2: thread u2af1_tsv_ch into VARIANT_FILTER by joining
        # with VEP_ANNOTATE.out.tsv on meta.id (both channels emit one tuple
        # per sample, so the join is 1:1 and cannot drop samples).
        (
            "        VEP_ANNOTATE(somaticseq_vcf_ch, reference_ch)\n"
            "\n"
            "        // Variant filter consumes blacklist; --blacklist arg from step 14.\n"
            "        VARIANT_FILTER(VEP_ANNOTATE.out.tsv, blacklist_ch)",
            "        VEP_ANNOTATE(somaticseq_vcf_ch, reference_ch)\n"
            "\n"
            "        // Join VEP output with U2AF1 rescue on meta.id. Both channels\n"
            "        // emit one tuple per sample so this is 1:1. variant_filter.py\n"
            "        // auto-discovers the staged u2af1 TSV by convention.\n"
            "        ch_filter_in = VEP_ANNOTATE.out.tsv.join(u2af1_tsv_ch)\n"
            "        VARIANT_FILTER(ch_filter_in, blacklist_ch)",
        ),
    ],
    Path("workflows/tspipe.nf"): [
        # Uncomment the ANNOTATION(...) call. Its 5-channel signature
        # matches the modified annotation.nf take block.
        (
            "    // ----- 6. Annotation: VEP -> ANNOVAR -> filter -> validator -> oncovi\n"
            "    // ANNOTATION(\n"
            "    //     ch_somaticseq_vcf,\n"
            "    //     ch_flt3_consensus,\n"
            "    //     VARIANT_CALLING.out.u2af1_tsv,\n"
            "    //     ch_blacklist,\n"
            "    //     ch_reference,\n"
            "    // )",
            "    // ----- 6. Annotation: VEP -> ANNOVAR -> filter -> validator -> oncovi\n"
            "    ANNOTATION(\n"
            "        ch_somaticseq_vcf,\n"
            "        ch_flt3_consensus,\n"
            "        VARIANT_CALLING.out.u2af1_tsv,\n"
            "        ch_blacklist,\n"
            "        ch_reference,\n"
            "    )",
        ),
    ],
}


# Signature used to confirm variant_filter.nf is in the latently-broken
# state we expect before rewriting it. The --input flag is the most
# distinctive marker; if it's missing, someone has touched the file
# since we last looked and we should NOT overwrite without checking.
VARIANT_FILTER_BUG_SIGNATURE = "--input ${annotated_tsv}"


def main():
    print("=== Pre-flight validation ===")

    # variant_filter.nf must exist AND still have the broken --input flag
    # we're patching out. If someone has already touched it, abort.
    vf_module = Path("modules/local/variant_filter.nf")
    if not vf_module.exists():
        sys.exit(f"FATAL: {vf_module} not found. Run from repo root.")
    if VARIANT_FILTER_BUG_SIGNATURE not in vf_module.read_text():
        sys.exit(
            f"FATAL: {vf_module} no longer contains '{VARIANT_FILTER_BUG_SIGNATURE}'.\n"
            f"       The file may have been touched since this patch was designed.\n"
            f"       Inspect manually before re-running."
        )
    print(f"  {vf_module}: confirmed broken state (--input flag present)")

    # Every str-replace target must appear exactly once.
    for path, replacements in PATCHES.items():
        if not path.exists():
            sys.exit(f"FATAL: {path} not found. Run from repo root.")
        text = path.read_text()
        for i, (old, _new) in enumerate(replacements, 1):
            count = text.count(old)
            if count == 0:
                sys.exit(f"FATAL: {path} replacement {i}: old_str not found")
            if count > 1:
                sys.exit(f"FATAL: {path} replacement {i}: old_str matched {count} times")
        print(f"  {path}: {len(replacements)} replacement(s) validated")
    print()

    # === Apply: variant_filter.nf is a full overwrite, others are str-replace.
    print("=== Applying patches ===")

    vf_backup = vf_module.with_name(
        vf_module.name + ".bak_annotation_wiring_" + TS
    )
    shutil.copy2(vf_module, vf_backup)
    print(f"  Backup: {vf_backup}")
    vf_module.write_text(VARIANT_FILTER_NEW_CONTENT)
    print(f"  Written: {vf_module} (full rewrite)")
    print()

    for path, replacements in PATCHES.items():
        backup = path.with_name(path.name + ".bak_annotation_wiring_" + TS)
        shutil.copy2(path, backup)
        print(f"  Backup: {backup}")

        text = path.read_text()
        for i, (old, new) in enumerate(replacements, 1):
            text = text.replace(old, new)
            print(f"  {path} replacement {i}: applied")
        path.write_text(text)
        print(f"  Written: {path}")
        print()

    print("Done. Verify with:")
    print(f"  git diff modules/local/variant_filter.nf")
    for path in PATCHES:
        print(f"  git diff {path}")


if __name__ == "__main__":
    main()
