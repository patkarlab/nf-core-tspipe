#!/usr/bin/env python3
"""
annotate.py

Annotate a SomaticSeq VCF with VEP and ANNOVAR, merge into a flat table.

Direct port of scripts/13_annotate.py from the production pipeline,
with these changes for nf-core integration:
  - --combined-vcf branch removed (annotate the SomaticSeq VCF only).
  - Hardcoded reference / VEP cache / ANNOVAR paths replaced with
    required CLI arguments (Nextflow passes them in via params).
  - Output goes to a single TSV at --output (default:
    <sample>.annotated.tsv in the current directory, matching
    Nextflow's work-dir convention).

The parsing and merging logic (parse_vcf_fields, parse_vep_csq,
parse_annovar_txt, merge_annotations, _get_info_value, _clean) is
preserved bit-for-bit from production so the output schema cannot drift.

Workflow:
  1. Parse the input VCF for FILTER, allelic depths (DP4), caller info
     (MVDKFP, NUM_TOOLS), and VAF.
  2. Run VEP: HGVS, consequences, gene symbols, population frequencies,
     using MANE Select transcripts. Invoked via `conda run -n vep vep ...`.
     This matches production exactly -- VEP needs its own Perl env so
     that DBI.pm and related modules resolve correctly via @INC.
  3. Run ANNOVAR: COSMIC ID, ClinVar significance, dbSNP rsID, gnomAD AF.
     Databases are probed at runtime; missing ones are skipped with a
     warning rather than failing the whole step.
  4. Merge all sources on chr:pos:ref:alt into a 29-column flat TSV.
     Empty cells and '.' are replaced with -1 for the downstream filter.

Usage (from the Nextflow module):
    annotate.py \\
        --somaticseq-vcf SAMPLE.somaticseq.vcf \\
        --sample-name SAMPLE \\
        --reference Homo_sapiens_assembly38.fasta \\
        --vep-cache /path/to/vep_cache \\
        --annovar-script /path/to/table_annovar.pl \\
        --annovar-db /path/to/humandb \\
        --output SAMPLE.annotated.tsv \\
        --vep-fork 8
"""

import argparse
import csv
import logging
import os
import re
import subprocess
import sys
import time

# Set up a simple console logger with timestamps. Every status message
# in this script flows through `log.<level>(...)`, which makes the run
# output easy to grep through after the fact.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# SomaticSeq caller order for the MVDKFP info field.
#
# IMPORTANT: SomaticSeq emits its native callers in the order
#     MuTect2, VarScan2, VarDict, Strelka
# (NOT VarDict before VarScan). Arbitrary callers (positions 5+) follow
# in the order they were passed via --arbitrary-snvs / --arbitrary-indels
# in the production 07_somaticseq.py orchestration step. Must stay in
# sync with CALLER_LABELS there.
SOMATICSEQ_CALLERS = ["Mutect2", "VarScan", "VarDict", "Strelka",
                      "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]

# Output columns. Order is fixed -- this is the schema that downstream
# consumers (VARIANT_FILTER, VARIANT_VALIDATOR, ONCOVI) depend on.
# Do not reorder or add columns without coordinating with those modules.
COLUMNS = [
    "Sample", "Chr", "Start", "End", "Ref", "Alt",
    "Gene", "Consequence", "HGVSc", "HGVSp", "IMPACT",
    "VariantCaller_Count", "Callers", "REF_COUNT", "ALT_COUNT", "VAF_pct",
    "SomaticSeq_Verdict",
    "COSMIC_ID", "ClinVar", "SIFT", "PolyPhen",
    "gnomAD_exome_AF", "gnomAD_genome_AF", "AF_1KG", "Max_AF", "rsID",
    "MANE_SELECT", "Canonical", "HGVSg", "Existing_variation",
]


def parse_args():
    """Define and parse the command-line arguments.

    argparse is Python's standard library for CLI parsing. We declare
    every required path explicitly (no defaults from environment) so
    the script's behaviour is fully captured by its invocation.
    """
    ap = argparse.ArgumentParser(
        description="Annotate a SomaticSeq VCF with VEP + ANNOVAR.",
    )
    ap.add_argument("--somaticseq-vcf", required=True,
                    help="SomaticSeq consensus VCF (input).")
    ap.add_argument("-s", "--sample-name", required=True,
                    help="Sample name; used as the output filename prefix.")
    ap.add_argument("-r", "--reference", required=True,
                    help="Reference FASTA (with .fai sibling indexed).")
    ap.add_argument("--vep-cache", required=True,
                    help="VEP cache directory containing "
                         "homo_sapiens/<version>_<assembly>/.")
    ap.add_argument("--annovar-script", required=True,
                    help="Path to ANNOVAR's table_annovar.pl perl script.")
    ap.add_argument("--annovar-db", required=True,
                    help="ANNOVAR humandb/ directory with hg38_*.txt databases.")
    ap.add_argument("-o", "--output", default=None,
                    help="Output TSV path. Default: <sample>.annotated.tsv "
                         "in the current directory.")
    ap.add_argument("--vep-fork", type=int, default=4,
                    help="VEP parallel forks (default: 4). The Nextflow "
                         "module passes task.cpus here.")
    return ap.parse_args()


def run(cmd, desc=None, env=None):  # [vepenv scoped PATH/PERL sanitisation]
    """Run a subprocess, log the command and any failure, return exit code.

    subprocess.run executes the command list and captures stdout/stderr.
    We log the command string before invocation (visible in .command.log
    when this runs under Nextflow) and the last 10 stderr lines on failure
    (the rest tends to be redundant).
    """
    if desc:
        log.info("%s", desc)
    log.info("  cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        log.error("  FAILED (exit %d)", result.returncode)
        for line in (result.stderr or "").strip().splitlines()[-10:]:
            log.error("    %s", line.strip())
    return result.returncode


def run_vep(vcf_in, vcf_out, reference, vep_cache, fork):
    """Run VEP via 'conda run -n vep'.

    The production pipeline invokes VEP through a host-side conda env
    named 'vep' that contains ensembl-vep 105.0. We replicate that exactly
    because VEP's Perl @INC paths are env-specific: a bare PATH export
    is not enough, the env must be activated for DBI.pm and related
    Bio::EnsEMBL::DBSQL modules to resolve. `conda run` handles activation
    for the duration of one command.
    """
    cmd = [
        "conda", "run", "-n", "vep", "vep",
        "--input_file", vcf_in,
        "--output_file", vcf_out,
        "--vcf",
        "--offline",
        "--cache",
        "--dir_cache", vep_cache,
        "--assembly", "GRCh38",
        "--fasta", reference,
        "--fork", str(fork),
        "--force_overwrite",
        "--flag_pick",       # [flagpick severity-based CSQ selection] keep ALL CSQ, tag one PICK=1; parser selects by severity
        "--everything",      # request the full annotation set
        "--hgvs",
        "--hgvsg",
        "--symbol",
        "--canonical",
        "--mane_select",
    ]
    # [vepenv scoped PATH/PERL sanitisation]
    # gandalf.config beforeScript prepends the targeted-seq env bin to PATH
    # (for ANNOVAR perl). That shadows VEP's own perl and aborts compilation
    # in Bio::EnsEMBL::VEP. Scope a cleaned env to the VEP subprocess only:
    # drop any targeted-seq bin from PATH and clear leaked Perl lib vars.
    vep_env = dict(os.environ)
    vep_env["PATH"] = os.pathsep.join(
        p for p in vep_env.get("PATH", "").split(os.pathsep)
        if "envs/targeted-seq/bin" not in p
    )
    for _v in ("PERL5LIB", "PERL_LOCAL_LIB_ROOT", "PERL_MM_OPT", "PERL_MB_OPT"):
        vep_env.pop(_v, None)
    return run(cmd, desc="Running VEP on " + os.path.basename(vcf_in),
               env=vep_env)


def run_annovar(vcf_in, out_prefix, annovar_script, annovar_db):
    """Run ANNOVAR table_annovar.pl with the five hg38 databases.

    Each database is probed before being added to the -protocol list.
    Missing databases are skipped with a warning, not fatal -- this is
    intentional so the pipeline keeps working if a database gets renamed
    or removed during a future upgrade.
    """
    protocols = []
    operations = []
    db_checks = [
        ("refGene", "g"),            # g = gene-based
        ("cosmic103", "f"),          # f = filter-based
        ("gnomad211_exome", "f"),
        ("clinvar_20220320", "f"),
        ("avsnp150", "f"),
    ]
    for db, op in db_checks:
        db_file = os.path.join(annovar_db, "hg38_" + db + ".txt")
        if os.path.isfile(db_file):
            protocols.append(db)
            operations.append(op)
        else:
            log.warning("ANNOVAR database not found, skipping: %s", db)

    if not protocols:
        log.error("No ANNOVAR databases available")
        return 1

    cmd = [
        "perl", annovar_script,
        vcf_in,
        annovar_db,
        "-buildver", "hg38",
        "-out", out_prefix,
        "-remove",
        "-protocol", ",".join(protocols),
        "-operation", ",".join(operations),
        "-nastring", ".",
        "-vcfinput",
    ]
    return run(cmd, desc="Running ANNOVAR on " + os.path.basename(vcf_in))


def _get_info_value(info_str, key):
    """Extract a value from a VCF INFO field by key.

    VCF INFO is a semicolon-separated list of key=value pairs (or bare
    flags). This finds the first field that starts with `key=` and
    returns the value, or empty string if absent.
    """
    for field in info_str.split(";"):
        if field.startswith(key + "="):
            return field[len(key) + 1:]
    return ""


def parse_vcf_fields(vcf_path):
    """Parse the input VCF to extract FILTER, allelic depths, caller info.

    Returns a dict keyed by chr:pos:ref:alt with these fields:
        filter      VCF FILTER column
        ref_count   reference allele depth (int, -1 if missing)
        alt_count   alternate allele depth (int, -1 if missing)
        vaf_pct     variant allele fraction as a percent (float, -1 if missing)
        num_tools   number of callers that supported the variant
        callers     comma-separated caller names

    PORT NOTE: this function is bit-for-bit identical to production's
    parse_vcf_fields() for vcf_type="somaticseq". The combined-VCF
    branch was removed entirely.
    """
    variants = {}

    with open(vcf_path) as f:
        for line in f:
            # Skip VCF header lines
            if line.startswith("#"):
                continue

            cols = line.strip().split("\t")
            if len(cols) < 8:
                continue

            chrom, pos, _, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
            filt = cols[6]
            info = cols[7]

            # Sentinel values: -1 = "not present", empty string = "no callers"
            ref_count = -1
            alt_count = -1
            vaf_pct = -1
            num_tools = -1
            callers = ""

            # Caller participation from MVDKFP (one-hot flags) + NUM_TOOLS
            mvdkfp = _get_info_value(info, "MVDKFP")
            num_tools_str = _get_info_value(info, "NUM_TOOLS")
            if num_tools_str:
                try:
                    num_tools = int(float(num_tools_str))
                except ValueError:
                    pass

            if mvdkfp:
                flags = mvdkfp.split(",")
                active = []
                for i, flag in enumerate(flags):
                    if flag == "1" and i < len(SOMATICSEQ_CALLERS):
                        active.append(SOMATICSEQ_CALLERS[i])
                callers = ",".join(active)

            # Allelic depths from DP4 in the FORMAT/sample columns.
            # DP4 = ref-forward, ref-reverse, alt-forward, alt-reverse.
            if len(cols) >= 10:
                fmt_keys = cols[8].split(":")
                fmt_vals = cols[9].split(":")
                fmt = dict(zip(fmt_keys, fmt_vals))

                dp4 = fmt.get("DP4", "")
                if dp4:
                    parts = dp4.split(",")
                    if len(parts) == 4:
                        try:
                            rf, rr, af, ar = [int(x) for x in parts]
                            ref_count = rf + rr
                            alt_count = af + ar
                        except ValueError:
                            pass

                # If the FORMAT field carries a VAF directly, use it.
                vaf_str = fmt.get("VAF", "")
                if vaf_str:
                    try:
                        vaf_pct = round(float(vaf_str) * 100, 2)
                    except ValueError:
                        pass

            # Fall back to alt/(ref+alt) if VAF wasn't directly given.
            if vaf_pct == -1 and ref_count >= 0 and alt_count >= 0:
                total = ref_count + alt_count
                if total > 0:
                    vaf_pct = round(alt_count / total * 100, 2)

            key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)
            variants[key] = {
                "filter": filt,
                "ref_count": ref_count,
                "alt_count": alt_count,
                "vaf_pct": vaf_pct,
                "num_tools": num_tools,
                "callers": callers,
            }

    log.info("Parsed %d variants from input VCF", len(variants))
    return variants


# [flagpick severity-based CSQ selection]
# Ensembl VEP consequence severity ordering (most severe first). Index = rank;
# lower index = more severe. Used to choose ONE CSQ block per variant when VEP
# is run with --flag_pick (which emits every transcript consequence). This is
# gene-agnostic: a coding consequence (missense/stop/frameshift) outranks a
# neighbouring transcript's upstream/downstream/intergenic MODIFIER, so an
# overlapping gene can no longer mask the clinically relevant call.
CONSEQUENCE_RANK = {
    name: i for i, name in enumerate([
        "transcript_ablation",
        "splice_acceptor_variant",
        "splice_donor_variant",
        "stop_gained",
        "frameshift_variant",
        "stop_lost",
        "start_lost",
        "transcript_amplification",
        "feature_elongation",
        "feature_truncation",
        "inframe_insertion",
        "inframe_deletion",
        "missense_variant",
        "protein_altering_variant",
        "splice_donor_5th_base_variant",
        "splice_region_variant",
        "splice_donor_region_variant",
        "splice_polypyrimidine_tract_variant",
        "incomplete_terminal_codon_variant",
        "start_retained_variant",
        "stop_retained_variant",
        "synonymous_variant",
        "coding_sequence_variant",
        "mature_miRNA_variant",
        "5_prime_UTR_variant",
        "3_prime_UTR_variant",
        "non_coding_transcript_exon_variant",
        "intron_variant",
        "NMD_transcript_variant",
        "non_coding_transcript_variant",
        "coding_transcript_variant",
        "upstream_gene_variant",
        "downstream_gene_variant",
        "TFBS_ablation",
        "TFBS_amplification",
        "TF_binding_site_variant",
        "regulatory_region_ablation",
        "regulatory_region_amplification",
        "regulatory_region_variant",
        "intergenic_variant",
        "sequence_variant",
    ])
}
_CONSEQUENCE_WORST = len(CONSEQUENCE_RANK) + 1


def _csq_severity(consequence):
    """Most-severe rank among the &-joined consequence terms of one CSQ block.

    VEP joins multiple terms with '&' (e.g. 'missense_variant&splice_region_variant').
    Returns the lowest (= most severe) rank; unknown terms sort last.
    """
    best = _CONSEQUENCE_WORST
    for term in str(consequence).split("&"):
        r = CONSEQUENCE_RANK.get(term, _CONSEQUENCE_WORST)
        if r < best:
            best = r
    return best


def _pick_csq(csq_blocks, csq_fields):
    """Choose ONE CSQ block from a variant's list of blocks.

    Selection order (gene-agnostic):
      1. most severe consequence (lowest _csq_severity)
      2. tie -> MANE Select transcript present
      3. tie -> VEP's own PICK flag (=='1') if a PICK field exists
      4. tie -> first block (input order)

    csq_blocks : list of dicts (field_name -> value)
    csq_fields : list of CSQ subfield names (for PICK/MANE_SELECT presence)
    """
    has_pick = "PICK" in csq_fields
    has_mane = "MANE_SELECT" in csq_fields

    def sort_key(idx_block):
        idx, block = idx_block
        sev = _csq_severity(block.get("Consequence", ""))
        mane = 0 if (has_mane and str(block.get("MANE_SELECT", "")).strip()) else 1
        pick = 0 if (has_pick and str(block.get("PICK", "")).strip() == "1") else 1
        return (sev, mane, pick, idx)

    indexed = list(enumerate(csq_blocks))
    indexed.sort(key=sort_key)
    return indexed[0][1]


def parse_vep_csq(vep_vcf):
    """Parse a VEP-annotated VCF, extracting CSQ fields per variant.

    Returns (variants, csq_fields) where:
      - csq_fields  is the list of CSQ subfield names from the header
                    (e.g. ['Allele', 'Consequence', 'IMPACT', 'SYMBOL', ...])
      - variants    is a dict keyed by chr:pos:ref:alt with subfield -> value

    VEP was invoked with --pick, so only the first CSQ annotation per
    variant is taken (VEP's pick algorithm chooses the canonical
    consequence). PORT NOTE: bit-for-bit identical to production's
    parse_vep_csq().
    """
    variants = {}
    csq_fields = []

    with open(vep_vcf) as f:
        for line in f:
            # The CSQ format string lives in the ##INFO=<ID=CSQ,...> header.
            if line.startswith("##INFO=<ID=CSQ"):
                match = re.search(r'Format: ([^"]+)', line)
                if match:
                    csq_fields = match.group(1).strip().split("|")
                continue
            if line.startswith("#"):
                continue

            cols = line.strip().split("\t")
            if len(cols) < 8:
                continue

            chrom, pos, _, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
            info = cols[7]

            csq_data = {}
            for field in info.split(";"):
                if field.startswith("CSQ="):
                    csq_str = field[4:]
                    # [flagpick severity-based CSQ selection]
                    # --flag_pick emits every transcript consequence (comma-
                    # separated). Parse them all, then choose one by severity
                    # so an overlapping neighbour cannot mask a coding call.
                    blocks = []
                    for one in csq_str.split(","):
                        values = one.split("|")
                        d = {}
                        for i, val in enumerate(values):
                            if i < len(csq_fields):
                                d[csq_fields[i]] = val
                        blocks.append(d)
                    if blocks:
                        csq_data = _pick_csq(blocks, csq_fields)
                    break

            key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)
            variants[key] = csq_data

    log.info("Parsed %d variants from VEP VCF (%d CSQ fields)",
             len(variants), len(csq_fields))
    return variants, csq_fields


def parse_annovar_txt(annovar_txt):
    """Parse ANNOVAR's multianno.txt (tab-separated) output.

    Returns a dict keyed by chr:pos:ref:alt. ANNOVAR's output columns
    depend on which protocols ran (refGene, cosmic103, etc.); each
    dict value is the raw row as a column -> value mapping, so the
    merge step can look up whichever fields it needs.

    PORT NOTE: bit-for-bit identical to production's parse_annovar_txt().
    """
    variants = {}
    if not os.path.isfile(annovar_txt):
        log.warning("ANNOVAR output not found: %s", annovar_txt)
        return variants

    with open(annovar_txt) as f:
        # csv.DictReader gives each row as a dict {column_name: value}.
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            chrom = row.get("Chr", "")
            pos = row.get("Start", "")
            ref = row.get("Ref", "")
            alt = row.get("Alt", "")
            key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)
            variants[key] = row

    log.info("Parsed %d variants from ANNOVAR txt", len(variants))
    return variants


def _clean(val):
    """Replace empty strings and '.' (VCF/ANNOVAR null) with '-1'.

    The downstream filter (VARIANT_FILTER) expects numeric fields to be
    sortable; '-1' is a sentinel that sorts low and is easy to grep.
    """
    if val is None or val == "" or val == ".":
        return "-1"
    return str(val)


def merge_annotations(vcf_fields, vep_variants, annovar_variants,
                      output_tsv, sample):
    """Merge VCF fields + VEP + ANNOVAR into the final flat TSV.

    PORT NOTE: bit-for-bit identical to production's merge_annotations()
    for vcf_type="somaticseq". The schema (the COLUMNS list at the top
    of this file) is the contract with downstream consumers; do not
    change it here without coordinating with VARIANT_FILTER and friends.
    """
    # Union of variant keys across all three sources -- a variant might
    # be present in VCF but not VEP (very rare; would imply VEP skipped
    # it), or in ANNOVAR but not the original VCF (impossible in
    # practice, included for symmetry).
    all_keys = set(vcf_fields.keys()) | set(vep_variants.keys()) | set(annovar_variants.keys())
    log.info("Merging annotations: %d VCF, %d VEP, %d ANNOVAR, %d total unique",
             len(vcf_fields), len(vep_variants), len(annovar_variants),
             len(all_keys))

    rows = []
    for key in sorted(all_keys):
        parts = key.split(":", 3)
        if len(parts) != 4:
            continue
        chrom, pos, ref, alt = parts

        vcf = vcf_fields.get(key, {})
        vep = vep_variants.get(key, {})
        ann = annovar_variants.get(key, {})

        # End position: pos + max(len(ref), 1) - 1.
        # max() guards against zero-length ref (insertion at pos).
        end = int(pos) + max(len(ref), 1) - 1

        row = {
            "Sample": sample,
            "Chr": chrom,
            "Start": pos,
            "End": str(end),
            "Ref": ref,
            "Alt": alt,
            # Gene/Consequence: VEP first, ANNOVAR refGene as fallback.
            "Gene": _clean(vep.get("SYMBOL", ann.get("Gene.refGene", ""))),
            "Consequence": _clean(vep.get("Consequence",
                                           ann.get("ExonicFunc.refGene", ""))),
            "HGVSc": _clean(vep.get("HGVSc", "")),
            "HGVSp": _clean(vep.get("HGVSp", "")),
            "IMPACT": _clean(vep.get("IMPACT", "")),
            "VariantCaller_Count": _clean(vcf.get("num_tools", -1)),
            "Callers": _clean(vcf.get("callers", "")),
            "REF_COUNT": _clean(vcf.get("ref_count", -1)),
            "ALT_COUNT": _clean(vcf.get("alt_count", -1)),
            "VAF_pct": _clean(vcf.get("vaf_pct", -1)),
            "SomaticSeq_Verdict": _clean(vcf.get("filter", "")),
            "COSMIC_ID": _clean(ann.get("cosmic103", "")),
            "ClinVar": _clean(ann.get("CLNSIG", ann.get("clinvar_20220320", ""))),
            "SIFT": _clean(vep.get("SIFT", "")),
            "PolyPhen": _clean(vep.get("PolyPhen", "")),
            "gnomAD_exome_AF": _clean(vep.get("gnomADe_AF", "")),
            "gnomAD_genome_AF": _clean(vep.get("gnomADg_AF",
                                                 ann.get("gnomad211_exome", ""))),
            "AF_1KG": _clean(vep.get("AF", "")),
            "Max_AF": _clean(vep.get("MAX_AF", "")),
            "rsID": _clean(ann.get("avsnp150",
                                    vep.get("Existing_variation", ""))),
            "MANE_SELECT": _clean(vep.get("MANE_SELECT", "")),
            "Canonical": _clean(vep.get("CANONICAL", "")),
            "HGVSg": _clean(vep.get("HGVSg", "")),
            "Existing_variation": _clean(vep.get("Existing_variation", "")),
        }
        rows.append(row)

    # csv.DictWriter writes the rows in the order specified by fieldnames,
    # ignoring any extra keys we might have added. extrasaction='ignore'
    # is defensive; we shouldn't have extra keys in practice.
    with open(output_tsv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    log.info("Wrote %d variants to %s", len(rows), output_tsv)
    return len(rows)


def main():
    t0 = time.time()
    args = parse_args()
    sample = args.sample_name
    output_tsv = args.output or sample + ".annotated.tsv"

    log.info("=== Annotation ===")
    log.info("Sample:         %s", sample)
    log.info("SomaticSeq VCF: %s", args.somaticseq_vcf)
    log.info("Reference:      %s", args.reference)
    log.info("VEP cache:      %s", args.vep_cache)
    log.info("ANNOVAR script: %s", args.annovar_script)
    log.info("ANNOVAR db:     %s", args.annovar_db)
    log.info("Output TSV:     %s", output_tsv)
    log.info("VEP forks:      %d", args.vep_fork)

    # Up-front validation of every file/dir we need. Fail fast with a
    # clear message rather than getting a cryptic error from VEP or
    # ANNOVAR halfway through.
    for path, label in [(args.somaticseq_vcf, "SomaticSeq VCF"),
                         (args.reference, "Reference"),
                         (args.annovar_script, "ANNOVAR table_annovar.pl")]:
        if not os.path.isfile(path):
            log.error("%s not found: %s", label, path)
            sys.exit(1)
    for path, label in [(args.vep_cache, "VEP cache"),
                         (args.annovar_db, "ANNOVAR database dir")]:
        if not os.path.isdir(path):
            log.error("%s not found: %s", label, path)
            sys.exit(1)

    # Intermediate filenames are derived from the sample name (not the
    # input VCF basename) so the Nextflow output globs are predictable
    # regardless of how the upstream module names the VCF.
    vep_vcf = sample + ".vep.vcf"
    annovar_prefix = sample
    annovar_txt = annovar_prefix + ".hg38_multianno.txt"

    # Step 1: parse caller metadata directly from the input VCF.
    vcf_fields = parse_vcf_fields(args.somaticseq_vcf)

    # Step 2: run VEP. Fatal on failure -- without VEP we have no
    # HGVS or gene annotations and the merge would be useless.
    rc = run_vep(args.somaticseq_vcf, vep_vcf, args.reference,
                 args.vep_cache, args.vep_fork)
    if rc != 0:
        log.error("VEP failed for %s", sample)
        sys.exit(1)

    # Step 3: run ANNOVAR. Non-fatal -- on failure we continue with
    # VEP-only annotations. COSMIC IDs and ClinVar significance will
    # be -1 in the output, but the variant rows still come through.
    rc = run_annovar(args.somaticseq_vcf, annovar_prefix,
                     args.annovar_script, args.annovar_db)
    if rc != 0:
        log.warning("ANNOVAR failed; continuing with VEP only")

    # Step 4: parse and merge.
    vep_variants, _ = parse_vep_csq(vep_vcf)
    annovar_variants = parse_annovar_txt(annovar_txt)
    n = merge_annotations(vcf_fields, vep_variants, annovar_variants,
                          output_tsv, sample)

    elapsed = time.time() - t0
    log.info("Wrote %d variants in %.0fs", n, elapsed)


if __name__ == "__main__":
    main()
