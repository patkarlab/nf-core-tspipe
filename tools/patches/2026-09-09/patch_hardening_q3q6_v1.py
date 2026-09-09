#!/usr/bin/env python3
"""HARDEN_Q3Q6_V1 -- pipeline hardening from the ChatGPT audit (verified 8 Sep 2026 against f830536).

Run from the nf-core-tspipe repo root on gandalf. Dry-run by default; --apply writes.
All edits are computed first and written only if every one of them succeeds
(all-or-nothing). Each file gets a .bak_HARDEN_Q3Q6_V1_<timestamp> backup.

Q3  workflows/tspipe.nf         validateSamplesheet() preflight mirroring assets/schema_input.json;
                                 called before any channel is built. Channel code untouched (hashes stable).
Q4a nextflow.config             process.shell = ['/bin/bash', '-euo', 'pipefail'] for every task.
Q4b modules/local/bam_quickcheck.nf (new) + include/call in tspipe.nf + publishDir in conf/modules.config:
                                 samtools quickcheck on the final BAM as its own process (no cached task invalidated).
Q4c pipefail-safety in module scripts that tolerated a failing producer:
                                 reconcnv.nf (5 x `ls ... | head -1`), bpt_cnvkit_reference.nf, bpt_cnv_loo_qc.nf,
                                 bpt_gatk_create_rc_pon.nf (`ls ... | wc -l`), cnvkit_pon_build.nf (`ls ... | tr`)
                                 get `|| true`. somaticseq.nf L197 (`grep -v '^#' "$SRC" | sort >>`) only with
                                 --with-somaticseq (costs a SOMATICSEQ_ENSEMBLE re-execution on resume; needed only if
                                 $SRC can be an empty per-caller VCF rather than the consensus).
Q5  bin/annotate.py             ANNOVAR failure, missing/empty multianno output, and missing ANNOVAR
                                 databases are fatal (exit 1). --annovar-allow-missing-db restores the skip.
Q6  bin/cnv_consensus_multi.py  max(hits) -> max(hits, key=overlap) at both sites (dicts are not orderable).

Verification (see the session notes): -preview with a broken samplesheet, -preview with the run8
samplesheet, check_annovar_fatal.py on a cached VEP_ANNOTATE task, the Q6 tie test, then a run8 resume.
"""
import argparse
import os
import re
import shutil
import sys
import time

TAG = "HARDEN_Q3Q6_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")


class PatchError(Exception):
    pass


def read(path):
    if not os.path.isfile(path):
        raise PatchError("missing file: %s" % path)
    with open(path) as f:
        return f.read()


def count(text, needle):
    return text.count(needle)


def replace_once(text, old, new, label):
    n = count(text, old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:70]))
    return text.replace(old, new)


def insert_before(text, anchor, block, label):
    return replace_once(text, anchor, block + anchor, label)


def insert_after(text, anchor, block, label):
    return replace_once(text, anchor, anchor + block, label)


def regex_sub_lines(text, pattern, repl, expected, label, skip_if=None):
    """Apply `repl` to every line matching `pattern`; require `expected` matches.
    skip_if = (needle, undo): a line containing `needle` that matches `pattern`
    once `needle` is replaced by `undo` is already patched and is left alone."""
    rx = re.compile(pattern)
    out = []
    hit = 0
    done = 0
    for line in text.split("\n"):
        if skip_if and skip_if[0] in line and rx.match(line.replace(skip_if[0], skip_if[1]).rstrip()):
            done += 1
            out.append(line)
            continue
        m = rx.match(line)
        if m:
            hit += 1
            out.append(rx.sub(repl, line))
        else:
            out.append(line)
    if hit + done != expected:
        raise PatchError("%s: matched %d lines (+%d already patched), expected %d" % (label, hit, done, expected))
    return "\n".join(out), hit


# ---------------------------------------------------------------------------
# Q3 + Q4b: workflows/tspipe.nf
# ---------------------------------------------------------------------------
Q3_FUNCTION = r'''// MARKER HARDEN_Q3_V1: samplesheet preflight (audit Q3). Mirrors assets/schema_input.json
// without the nf-schema plugin. Every problem is collected and reported at once, before any
// channel is built or task submitted. The channel code below is unchanged (meta/hashes stable).
def validateSamplesheet(String path) {
    def required = ['sample', 'fastq_1', 'fastq_2']
    def allowedSex = ['male', 'female', 'unknown', '']
    def rows = file(path, checkIfExists: true).splitCsv(header: true)
    if( !rows ) {
        error "[PREFLIGHT] samplesheet ${path} has no data rows"
    }
    def header = rows[0].keySet() as List
    def missing = required - header
    if( missing ) {
        error "[PREFLIGHT] samplesheet ${path} is missing column(s): ${missing.join(', ')} (found: ${header.join(', ')})"
    }
    def problems = []
    def seen = [:]
    rows.eachWithIndex { row, i ->
        def line = i + 2
        def id = (row.sample ?: '').toString().trim()
        if( !id ) {
            problems << "line ${line}: empty sample id"
        } else if( !(id ==~ /^\S+$/) ) {
            problems << "line ${line}: sample id '${id}' contains whitespace"
        } else if( seen.containsKey(id) ) {
            problems << "line ${line}: duplicate sample id '${id}' (first seen on line ${seen[id]})"
        } else {
            seen[id] = line
        }
        ['fastq_1', 'fastq_2'].each { col ->
            def v = (row[col] ?: '').toString().trim()
            if( !v ) {
                problems << "line ${line}: ${col} is empty"
            } else if( !(v ==~ /^\S+\.f(ast)?q\.gz$/) ) {
                problems << "line ${line}: ${col} '${v}' does not end in .fq.gz or .fastq.gz"
            } else if( !file(v).exists() ) {
                problems << "line ${line}: ${col} not found: ${v}"
            }
        }
        def sex = (row.sex ?: '').toString().trim()
        if( !(sex in allowedSex) ) {
            problems << "line ${line}: sex '${sex}' is not one of male/female/unknown (or empty)"
        }
    }
    if( problems ) {
        error "[PREFLIGHT] samplesheet ${path} failed validation (${problems.size()} problem(s)):\n  " + problems.join('\n  ')
    }
    log.info "[PREFLIGHT] samplesheet ${path}: ${rows.size()} sample(s) validated"
}

'''

Q3_CALL_ANCHOR = '    if (!params.exonwise_bed) { error "Missing --exonwise_bed (Exonwise hg38 BED for per-exon coverage)" }\n'
Q3_CALL = '    validateSamplesheet(params.input)   // MARKER HARDEN_Q3_V1: fail before any task is submitted\n'

Q4B_INCLUDE_ANCHOR = "include { PREPROCESSING       } from '../subworkflows/local/preprocessing'\n"
Q4B_INCLUDE = "include { BAM_QUICKCHECK      } from '../modules/local/bam_quickcheck'   // MARKER HARDEN_Q4_V1\n"
Q4B_CALL_ANCHOR = "    ch_exon_coverage = PREPROCESSING.out.exon_coverage   // [meta, exon_coverage.tsv]\n"
Q4B_CALL = """
    // MARKER HARDEN_Q4_V1: samtools quickcheck on the final BAM (audit Q4). A separate process so
    // that no cached task is invalidated; a truncated or unreadable BAM fails the run here.
    BAM_QUICKCHECK(ch_final_bam)
"""


def patch_tspipe(text):
    if "MARKER HARDEN_Q3_V1" in text and "MARKER HARDEN_Q4_V1" in text:
        return text, "skip"
    if "MARKER HARDEN_Q3_V1" not in text:
        text = insert_before(text, "workflow TSPIPE {\n", Q3_FUNCTION, "tspipe.nf Q3 function")
        text = insert_after(text, Q3_CALL_ANCHOR, Q3_CALL, "tspipe.nf Q3 call")
    if "MARKER HARDEN_Q4_V1" not in text:
        text = insert_after(text, Q4B_INCLUDE_ANCHOR, Q4B_INCLUDE, "tspipe.nf Q4b include")
        text = insert_after(text, Q4B_CALL_ANCHOR, Q4B_CALL, "tspipe.nf Q4b call")
    return text, "patch"


# ---------------------------------------------------------------------------
# Q4a: nextflow.config
# ---------------------------------------------------------------------------
Q4A_ANCHOR = "includeConfig 'conf/modules.config'\n"
Q4A_BLOCK = """
// MARKER HARDEN_Q4_V1: every task shell runs with pipefail (audit Q4; previously set in 8 of 75
// module scripts only), so a failing producer in a pipe fails the task instead of being masked
// by the consumer's exit status. Module scripts that legitimately tolerate a failing producer
// carry an explicit `|| true` (reconcnv, bpt_*, cnvkit_pon_build, somaticseq).
process.shell = ['/bin/bash', '-euo', 'pipefail']
"""


def patch_nextflow_config(text):
    if "MARKER HARDEN_Q4_V1" in text:
        return text, "skip"
    return insert_after(text, Q4A_ANCHOR, Q4A_BLOCK, "nextflow.config Q4a"), "patch"


# ---------------------------------------------------------------------------
# Q4b: modules/local/bam_quickcheck.nf (new) + conf/modules.config publishDir
# ---------------------------------------------------------------------------
BAM_QUICKCHECK_NF = r'''/*
 * modules/local/bam_quickcheck.nf
 *
 * MARKER HARDEN_Q4_V1 (audit Q4): samtools quickcheck on the final (ABRA2) BAM.
 * Fails the run on a truncated or unreadable BAM. Runs as its own process so
 * that adding it does not invalidate any cached task; downstream processes are
 * not gated on it, but a failure here terminates the run.
 */
process BAM_QUICKCHECK {
    tag "$meta.id"
    cpus 1
    memory '2 GB'
    container 'quay.io/biocontainers/samtools:1.18--h50ea8bc_1'

    input:
    tuple val(meta), path(bam), path(bai)

    output:
    tuple val(meta), path("${meta.id}.quickcheck.txt"), emit: report
    path "versions.yml",                                emit: versions

    script:
    """
    if samtools quickcheck -vv ${bam} > ${meta.id}.quickcheck.txt 2>&1; then
        echo "OK ${bam} (\$(stat -L -c %s ${bam}) bytes)" >> ${meta.id}.quickcheck.txt
    else
        echo "[BAM_QUICKCHECK] ${meta.id}: ${bam} failed samtools quickcheck" >&2
        cat ${meta.id}.quickcheck.txt >&2
        exit 1
    fi

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samtools: \$(samtools --version | head -n1 | sed 's/samtools //')
    END_VERSIONS
    """

    stub:
    """
    echo "OK ${bam} (stub)" > ${meta.id}.quickcheck.txt
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samtools: stub
    END_VERSIONS
    """
}
'''

MODCONF_ANCHOR = "    withName: 'BWA_MEM' {\n"
MODCONF_BLOCK = """    // MARKER HARDEN_Q4_V1: final-BAM integrity check
    withName: 'BAM_QUICKCHECK' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/qc" },
            mode: params.publish_dir_mode,
            pattern: '*.quickcheck.txt'
        ]
    }

"""


def patch_modules_config(text):
    if "MARKER HARDEN_Q4_V1" in text:
        return text, "skip"
    return insert_before(text, MODCONF_ANCHOR, MODCONF_BLOCK, "modules.config Q4b"), "patch"


# ---------------------------------------------------------------------------
# Q4c: pipefail-safety in module scripts
# ---------------------------------------------------------------------------
# Each entry: (path, regex matching the whole line, expected number of lines).
# The line's closing text is captured in group 1 and ' || true' inserted before
# the final ')' (command substitutions) or appended (plain pipelines).
Q4C_SUBST_LINES = [
    ("modules/local/reconcnv.nf",
     r"^(\s*(?:RATIO|GENOME|SEG|HETVCF|CONF)=\\\$\(ls [^\n]*\| head -1)\)\s*$", 5),
    ("modules/local/bpt_cnvkit_reference.nf",
     r"^(\s*n_[ta]=\\\$\(ls [^\n]*2>/dev/null \| wc -l)\)\s*$", 2),
    ("modules/local/bpt_cnv_loo_qc.nf",
     r"^(\s*n_[ta]=\\\$\(ls [^\n]*2>/dev/null \| wc -l)\)\s*$", 1),
    ("modules/local/bpt_gatk_create_rc_pon.nf",
     r"^(\s*n=\\\$\(ls [^\n]*2>/dev/null \| wc -l)\)\s*$", 1),
    ("modules/local/cnvkit_pon_build.nf",
     r"^(\s*BAMS=\\\$\(ls \*\.final\.bam 2>/dev/null \| sort \| tr '\\\\n' ' ')\)\s*$", 1),
]
Q4C_APPEND_LINES = [
    ("modules/local/somaticseq.nf",
     r"^(\s*grep -v '\^#' \"\\\$SRC\" \| sort -k1,1V -k2,2g >> \"\\\$SORTED\")\s*$", 1),
]


def patch_q4c_subst(text, pattern, expected, label):
    return regex_sub_lines(text, pattern, r"\1 || true)", expected, label, skip_if=(" || true)", ")"))


def patch_q4c_append(text, pattern, expected, label):
    return regex_sub_lines(text, pattern, r"\1 || true", expected, label, skip_if=(" || true", ""))


# ---------------------------------------------------------------------------
# Q5: bin/annotate.py
# ---------------------------------------------------------------------------
Q5_EDITS = [
    # argparse flag
    ('    ap.add_argument("--cava-vcf", default=None,   # CAVA_V1b (N3)\n',
     '    ap.add_argument("--annovar-allow-missing-db", action="store_true",   # HARDEN_Q5_V1\n'
     '                    help="Skip ANNOVAR databases that are missing from --annovar-db instead of "\n'
     '                         "aborting (default: a missing database is fatal).")\n'
     '    ap.add_argument("--cava-vcf", default=None,   # CAVA_V1b (N3)\n',
     "before"),
    # run_annovar signature + docstring
    ('def run_annovar(vcf_in, out_prefix, annovar_script, annovar_db):\n'
     '    """Run ANNOVAR table_annovar.pl with the five hg38 databases.\n'
     '\n'
     '    Each database is probed before being added to the -protocol list.\n'
     '    Missing databases are skipped with a warning, not fatal -- this is\n'
     '    intentional so the pipeline keeps working if a database gets renamed\n'
     '    or removed during a future upgrade.\n'
     '    """\n',
     'def run_annovar(vcf_in, out_prefix, annovar_script, annovar_db, allow_missing_db=False):\n'
     '    """Run ANNOVAR table_annovar.pl with the five hg38 databases.\n'
     '\n'
     '    Each database is probed before being added to the -protocol list.\n'
     '    HARDEN_Q5_V1 (audit Q5): a missing database is fatal (return 1) unless\n'
     '    allow_missing_db is set -- a silently absent ClinVar table would switch\n'
     '    the CLINVAR_BENIGN demotion off without any visible failure.\n'
     '    """\n'
     '    missing = []\n',
     "replace"),
    ('        else:\n'
     '            log.warning("ANNOVAR database not found, skipping: %s", db)\n'
     '\n'
     '    if not protocols:\n'
     '        log.error("No ANNOVAR databases available")\n'
     '        return 1\n',
     '        else:\n'
     '            missing.append(db)\n'
     '            log.warning("ANNOVAR database not found: %s (%s)", db, db_file)\n'
     '\n'
     '    if missing and not allow_missing_db:   # HARDEN_Q5_V1\n'
     '        log.error("ANNOVAR database(s) missing under %s: %s -- fatal; pass "\n'
     '                  "--annovar-allow-missing-db to continue without them",\n'
     '                  annovar_db, ", ".join(missing))\n'
     '        return 1\n'
     '    if not protocols:\n'
     '        log.error("No ANNOVAR databases available")\n'
     '        return 1\n',
     "replace"),
    # main(): fatal on failure, and on missing/empty output
    ('    # Step 3: run ANNOVAR. Non-fatal -- on failure we continue with\n'
     '    # VEP-only annotations. COSMIC IDs and ClinVar significance will\n'
     '    # be -1 in the output, but the variant rows still come through.\n'
     '    rc = run_annovar(args.somaticseq_vcf, annovar_prefix,\n'
     '                     args.annovar_script, args.annovar_db)\n'
     '    if rc != 0:\n'
     '        log.warning("ANNOVAR failed; continuing with VEP only")\n',
     '    # Step 3: run ANNOVAR. HARDEN_Q5_V1 (audit Q5): fatal on failure. Continuing\n'
     '    # with VEP only would leave ClinVar/COSMIC/gnomAD/avsnp at -1 and silently\n'
     '    # switch the CLINVAR_BENIGN demotion off in VARIANT_FILTER.\n'
     '    rc = run_annovar(args.somaticseq_vcf, annovar_prefix,\n'
     '                     args.annovar_script, args.annovar_db,\n'
     '                     allow_missing_db=args.annovar_allow_missing_db)\n'
     '    if rc != 0:\n'
     '        log.error("ANNOVAR failed for %s (exit %d) -- aborting", sample, rc)\n'
     '        sys.exit(1)\n'
     '    if not os.path.isfile(annovar_txt) or os.path.getsize(annovar_txt) == 0:\n'
     '        log.error("ANNOVAR exited 0 but %s is missing or empty -- aborting", annovar_txt)\n'
     '        sys.exit(1)\n',
     "replace"),
]


def patch_annotate(text):
    if "HARDEN_Q5_V1" in text:
        return text, "skip"
    for old, new, mode in Q5_EDITS:
        if mode == "before":
            text = insert_before(text, old, new[: -len(old)], "annotate.py Q5 argparse")
        else:
            text = replace_once(text, old, new, "annotate.py Q5 " + old.split("\n")[0][:40])
    return text, "patch"


# ---------------------------------------------------------------------------
# Q6: bin/cnv_consensus_multi.py
# ---------------------------------------------------------------------------
def patch_cmx(text):
    if "HARDEN_Q6_V1" in text:
        return text, "skip"
    text, n = regex_sub_lines(
        text,
        r"^(\s*)top = max\(hits\)\[1\]$",
        r"\1top = max(hits, key=lambda h: h[0])[1]   # HARDEN_Q6_V1: key on overlap; segment dicts are not orderable (TypeError on ties)",
        2, "cnv_consensus_multi.py Q6")
    return text, "patch"


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    ap.add_argument("--with-somaticseq", action="store_true",
                    help="also add `|| true` to somaticseq.nf L197 (see module docstring)")
    args = ap.parse_args()
    os.chdir(args.repo)
    if not os.path.isfile("workflows/tspipe.nf") or not os.path.isfile("nextflow.config"):
        print("[error] not an nf-core-tspipe repo root: %s" % os.getcwd())
        sys.exit(2)

    plan = []   # (path, new_text, status)
    try:
        for path, fn in [("workflows/tspipe.nf", patch_tspipe),
                         ("nextflow.config", patch_nextflow_config),
                         ("conf/modules.config", patch_modules_config),
                         ("bin/annotate.py", patch_annotate),
                         ("bin/cnv_consensus_multi.py", patch_cmx)]:
            new, status = fn(read(path))
            plan.append((path, new, status))
        for path, pattern, expected in Q4C_SUBST_LINES:
            new, hit = patch_q4c_subst(read(path), pattern, expected, path)
            plan.append((path, new, "patch" if hit else "skip"))
        if args.with_somaticseq:
            for path, pattern, expected in Q4C_APPEND_LINES:
                new, hit = patch_q4c_append(read(path), pattern, expected, path)
                plan.append((path, new, "patch" if hit else "skip"))
        newmod = "modules/local/bam_quickcheck.nf"
        if os.path.isfile(newmod):
            existing = read(newmod)
            plan.append((newmod, existing if "MARKER HARDEN_Q4_V1" in existing else BAM_QUICKCHECK_NF,
                         "skip" if "MARKER HARDEN_Q4_V1" in existing else "patch"))
        else:
            plan.append((newmod, BAM_QUICKCHECK_NF, "create"))
    except PatchError as e:
        print("[error] %s" % e)
        print("[error] nothing written")
        sys.exit(1)

    for path, new, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write")
        return

    for path, new, status in plan:
        if status == "skip":
            continue
        if status != "create":
            bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
            shutil.copy2(path, bak)
            print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
