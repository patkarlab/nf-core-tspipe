#!/usr/bin/env python3
"""
apply_vep_annotate_port.py

Wires bin/annotate.py into the nf-core port: rewrites the
VEP_ANNOTATE module body, fixes the (broken) ANNOVAR database path in
gandalf.config, adds a new params.annovar_script for the perl entrypoint,
and registers that param in nextflow.config's defaults block.

Pre-flight requires that bin/annotate.py already exists in the repo
(deploy that file separately before running this script).

Files modified:
  1. modules/local/vep_annotate.nf  -- stub body replaced with real
                                       invocation of bin/annotate.py
  2. conf/gandalf.config            -- annovar_db pointed at real path,
                                       new params.annovar_script added
  3. nextflow.config                -- params.annovar_script = null
                                       added to defaults

Backups:
  conf/gandalf.config.bak_vep_annotate_port_<timestamp>
  conf/../modules/local/vep_annotate.nf.bak_vep_annotate_port_<timestamp>
  nextflow.config.bak_vep_annotate_port_<timestamp>
"""
import shutil
import sys
from pathlib import Path
from datetime import datetime

TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# --- New content for modules/local/vep_annotate.nf -------------------------
#
# Replaces the stub body entirely. Structure follows the variant_filter.nf
# template: conda directive declared for portability, beforeScript not
# needed (the gandalf.config-level beforeScript already exposes the
# targeted-seq env's bin to PATH; VEP itself is invoked via 'conda run
# -n vep' inside annotate.py). Output filename matches the existing
# stub declaration so the subworkflow's wiring keeps working.
VEP_ANNOTATE_NEW_CONTENT = '''/*
 * modules/local/vep_annotate.nf
 *
 * Annotate a SomaticSeq VCF with VEP + ANNOVAR, emit a merged 29-column
 * flat TSV. Wraps bin/annotate.py, which is a port of production
 * scripts/13_annotate.py with the combined-VCF branch removed.
 *
 * VEP runs via `conda run -n vep vep ...` inside annotate.py -- the vep
 * env has its own Perl @INC and we must let conda activate it for the
 * duration of the vep invocation. ANNOVAR runs via the targeted-seq
 * env's perl, already on PATH via gandalf.config beforeScript.
 *
 * Inputs:
 *   vcf       -- SomaticSeq consensus VCF
 *   fasta+fai+dict -- reference genome (staged together by Nextflow)
 *
 * Output:
 *   ${meta.id}.annotated.tsv  -- 29-column flat TSV, schema in
 *                                bin/annotate.py COLUMNS
 *   versions.yml              -- software versions for the final report
 */

process VEP_ANNOTATE {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'conda-forge::pandas=2.1.4'

    input:
        tuple val(meta), path(vcf)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}.annotated.tsv"), emit: tsv
        path  "versions.yml",                              emit: versions

    stub:
        // Touch the declared outputs so the DAG validates in -stub mode
        // without actually running VEP or ANNOVAR.
        """
        touch ${meta.id}.annotated.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        annotate.py \\\\
            --somaticseq-vcf ${vcf} \\\\
            --sample-name ${meta.id} \\\\
            --reference ${fasta} \\\\
            --vep-cache ${params.vep_cache} \\\\
            --annovar-script ${params.annovar_script} \\\\
            --annovar-db ${params.annovar_db} \\\\
            --output ${meta.id}.annotated.tsv \\\\
            --vep-fork ${task.cpus}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \\$(python --version 2>&1 | sed 's/Python //')
            perl:   \\$(perl -e 'print substr(\\$^V, 1)')
        END_VERSIONS
        """
}
'''

# Each (path, list-of-replacements) pair. For files we modify with
# string replacement, each replacement is (old_str, new_str). For
# vep_annotate.nf we use a full-content rewrite, which is represented
# by a single replacement that matches the entire current file body.
PATCHES = {
    Path("conf/gandalf.config"): [
        # Fix the annovar_db path (currently pointing at a non-existent
        # ${pipeline_root}/references/annovar_db) and add a new
        # annovar_script param. annovar_db moves from references/ to
        # software/annovar/humandb to match where the databases actually
        # live on the production tree.
        (
            "    // Annotation databases\n"
            "    vep_cache          = \"${params.pipeline_root}/references/vep_cache\"\n"
            "    annovar_db         = \"${params.pipeline_root}/references/annovar_db\"",
            "    // Annotation databases.\n"
            "    // The ${params.pipeline_root}/references/annovar_db path used\n"
            "    // by earlier configs did not exist on disk; the real ANNOVAR\n"
            "    // install lives under software/annovar/. annovar_script points\n"
            "    // at the perl entrypoint (table_annovar.pl), annovar_db at the\n"
            "    // humandb/ directory of databases.\n"
            "    vep_cache          = \"${params.pipeline_root}/references/vep_cache\"\n"
            "    annovar_script     = \"${params.pipeline_root}/software/annovar/table_annovar.pl\"\n"
            "    annovar_db         = \"${params.pipeline_root}/software/annovar/humandb\"",
        ),
    ],
    Path("nextflow.config"): [
        # Register the new annovar_script param next to the existing
        # vep_cache / annovar_db defaults. Keeps the params block
        # self-documenting.
        (
            "    // ---- Annotation -----------------------------------------------------\n"
            "    vep_cache          = null\n"
            "    annovar_db         = null",
            "    // ---- Annotation -----------------------------------------------------\n"
            "    vep_cache          = null\n"
            "    annovar_script     = null   // path to ANNOVAR's table_annovar.pl\n"
            "    annovar_db         = null",
        ),
    ],
}

# Signature we use to verify vep_annotate.nf is still a stub before we
# overwrite it. If someone has already filled in the body, this check
# fails and the patch aborts -- safer than silently overwriting work.
VEP_ANNOTATE_STUB_SIGNATURE = "TODO: replace this stub with the tool invocation"


def main():
    print("=== Pre-flight validation ===")

    # Pre-flight 1: bin/annotate.py must already be in place.
    annotate_py = Path("bin/annotate.py")
    if not annotate_py.exists():
        sys.exit(
            "FATAL: bin/annotate.py not found.\n"
            "       Deploy that file BEFORE running this patch:\n"
            "         mv ~/inbox/from_claude/annotate.py bin/annotate.py\n"
            "         chmod +x bin/annotate.py"
        )
    if not (annotate_py.stat().st_mode & 0o111):
        sys.exit(
            "FATAL: bin/annotate.py exists but is not executable.\n"
            "       Run: chmod +x bin/annotate.py"
        )
    print(f"  bin/annotate.py: present and executable")

    # Pre-flight 2: vep_annotate.nf must currently be a stub.
    vep_module = Path("modules/local/vep_annotate.nf")
    if not vep_module.exists():
        sys.exit(f"FATAL: {vep_module} not found. Run from nf-core-tspipe repo root.")
    if VEP_ANNOTATE_STUB_SIGNATURE not in vep_module.read_text():
        sys.exit(
            f"FATAL: {vep_module} does not look like a stub anymore.\n"
            f"       The marker '{VEP_ANNOTATE_STUB_SIGNATURE}' is missing.\n"
            f"       Has it already been filled in? Inspect manually before re-running."
        )
    print(f"  {vep_module}: confirmed stub state")

    # Pre-flight 3: validate every str-replace target exists exactly once.
    for path, replacements in PATCHES.items():
        if not path.exists():
            sys.exit(f"FATAL: {path} not found. Run from nf-core-tspipe repo root.")
        text = path.read_text()
        for i, (old, _new) in enumerate(replacements, 1):
            count = text.count(old)
            if count == 0:
                sys.exit(f"FATAL: {path} replacement {i}: old_str not found")
            if count > 1:
                sys.exit(f"FATAL: {path} replacement {i}: old_str matched {count} times")
        print(f"  {path}: {len(replacements)} replacement(s) validated")
    print()

    # === Apply: vep_annotate.nf is a full overwrite; the others are
    # surgical string replacements. Backup every file before changing it.
    print("=== Applying patches ===")

    vep_backup = vep_module.with_name(
        vep_module.name + ".bak_vep_annotate_port_" + TS
    )
    shutil.copy2(vep_module, vep_backup)
    print(f"  Backup: {vep_backup}")
    vep_module.write_text(VEP_ANNOTATE_NEW_CONTENT)
    print(f"  Written: {vep_module} (full rewrite)")
    print()

    for path, replacements in PATCHES.items():
        backup = path.with_name(path.name + ".bak_vep_annotate_port_" + TS)
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
    print(f"  git diff modules/local/vep_annotate.nf")
    for path in PATCHES:
        print(f"  git diff {path}")


if __name__ == "__main__":
    main()
