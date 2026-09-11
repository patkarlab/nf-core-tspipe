#!/usr/bin/env python3
"""
RELEASE_DOCS_V1 -- align the release paperwork with the v1.0.0 freeze.

Three independent edits, applied all-or-nothing:

  1. nextflow.config  : manifest.version '0.1.0dev' -> '1.0.0'
  2. docs/RELEASE_NOTES.md : the Deployment section points at
     docs/sops/install_clinical23.md, which does not exist. Repoint it at
     the controlled SOP and name the sections that actually cover install
     and porting.
  3. CHANGELOG.md     : add a [1.0.0] entry for the September work, demote
     the old "[Unreleased] - 0.1.0-dev" block to a dated [0.1.0-dev]
     section, open a fresh [Unreleased] for the v1.1 line, and fix the
     link-reference footer.

Idempotent: each edit is skipped when its MARKER is already present.
Dry-run by default; pass --apply to write. Timestamped .bak_ backups.

Usage:
    python3 tools/patches/2026-09-11/patch_release_docs_v1.py            # dry run
    python3 tools/patches/2026-09-11/patch_release_docs_v1.py --apply
"""

import argparse
import datetime as _dt
import shutil
import sys
from pathlib import Path

TAG = "release_docs_v1"

# ---------------------------------------------------------------------------
# 1. nextflow.config
# ---------------------------------------------------------------------------

NF_OLD = "    version         = '0.1.0dev'"
NF_NEW = "    version         = '1.0.0'"
NF_MARKER = NF_NEW

# ---------------------------------------------------------------------------
# 2. docs/RELEASE_NOTES.md
# ---------------------------------------------------------------------------

RN_OLD = """`docs/sops/install_clinical23.md` describes installing this release on a new host: prerequisites,
loading the image set, placing the reference data against the manifest, verification with the stub
DAG, and the eight-sample golden regression."""

RN_NEW = """`docs/sops/SOP-TSPIPE-001.md` is the controlled document for this release. Section 7 covers
installation on a new host from nothing (host software, image transfer and sandboxes, reference
data, credentials, site-config authoring) with installation qualification in 7.9 and operational
qualification in 7.10; section 12 covers porting to a further server and the site-specific
decision table; section 14 covers backup, archive and restore of the container images. Annex A is
the clinical-23 installation record, including the exact run procedure.

Install-time helpers: `tools/make_sandboxes.sh` (image sandboxes), `tools/verify_install.sh`
(toolchain, images against `docs/release/image_checksums.md5`, references against
`docs/release/reference_manifest.tsv`), and `tools/compare_runs.py` for the eight-sample golden
regression against the accepted run."""

RN_MARKER = "`docs/sops/SOP-TSPIPE-001.md` is the controlled document for this release."

# ---------------------------------------------------------------------------
# 3. CHANGELOG.md
# ---------------------------------------------------------------------------

CL_OLD = """## [Unreleased] — 0.1.0-dev

The pre-1.0 working line. Features below are present and validated on
gandalf; the version stays at `0.1.0-dev` until the first tagged
GitHub Release.
"""

CL_NEW = """## [Unreleased]

The v1.1 working line. Nothing here is part of a tagged release. Items deferred from 1.0.0 are
listed under "Deferred to 1.1" below.

## [1.0.0] — 2026-09-10

Clinical freeze. Frozen on the development host on 2026-09-10, deployed to the clinical HPC and
accepted on 2026-09-11 after a cross-host golden regression. This is the version used for
reporting on the Twist myeloid panel. `docs/RELEASE_NOTES.md` holds the release definition;
`docs/sops/SOP-TSPIPE-001.md` governs installation, operation and change control.

### Added — release engineering

- **Full containerisation.** `local/tspipe-host:v1.1` (`containers/tspipe-host/`) carries the
  seven validated conda environments under `/opt/envs/` and Strelka2, ANNOVAR, OncoVI and the
  VarDict helpers under `/opt/`. No process depends on a conda environment, a `beforeScript` PATH
  export or a host tool. `conf/containers.config` assigns the image and the per-process `PATH`;
  site profiles carry only paths, executor settings and resources.
- **Release artefacts.** `docs/release/image_checksums.md5` (17 images) and
  `docs/release/reference_manifest.tsv` (44 reference entries with size and md5).
- **Second site.** `conf/clinical23.config` (PBS Pro), `tools/make_sandboxes.sh`,
  `tools/verify_install.sh` (installation qualification) and `tools/compare_runs.py` (content-aware
  run comparison, the golden-regression method).
- **Controlled documentation.** `docs/sops/SOP-TSPIPE-001.md` and its PDF render: dependencies,
  installation from nothing, IQ/OQ, routine operation, troubleshooting, frozen configuration and
  change control, porting, backup and restore, plus a site annex.
- Nextflow pinned at `!>=25.10.4`; `manifest.version` set to `1.0.0`.

### Added — annotation

- **CAVA 2.0.15** against the MANE 1.5 GRCh38 RefSeq catalog, for clinical HGVS nomenclature.
  Card and report nomenclature preference is VariantValidator, then CAVA, then VEP.
- **MANE-Select-first consequence selection** in VEP output, replacing severity-first selection.
- **MNV merge**: multi-nucleotide variants decomposed by the callers are reconstructed (gap
  <= 2 bp) and added alongside their tagged components, with caller support restored.
- **Alternative-transcript table**: every VEP transcript block retained in a `VEP_Transcripts`
  column and shown in the variant detail view.
- **External annotators**: GeneBe, MobiDetails and CancerVar on by default; OncoKB opt-in with a
  token supplied through an untracked credentials file.
- **Spike-in sites**: genotyping and coverage of the panel's regulatory and germline-risk spike-in
  targets, with their own report tab.

### Added — copy number

- Six-arm sex-stratified consensus: CNVkit, GATK ModelSegments, DECoN (exon level), PureCN,
  PURPLE (hmftools AMBER/COBALT, tumour-only targeted) and a per-chromosome-arm B-allele-frequency
  detector for cnLOH and allelic imbalance.
- Consensus gene table annotated with cytoband, ClinGen haploinsufficiency and triplosensitivity,
  and driver role; CNV gene blacklist asset.
- Visualisation: genome-wide overview (depth, BAF arm medians, PURPLE copy number), target-space
  chromosome pages with cytoband strip and per-gene exon panels, a dedicated 17p page, and
  reconCNV as an interactive view. CNV report tab reorganised into sub-tabs.

### Added — QC and filtering

- **Genotype-based sex check** from chrX heterozygosity with depth confirmation. A mismatch
  against the samplesheet forces a `REVIEW` verdict; it never stops the run.
- **QC page rewrite**: median of per-exon coverage as the headline metric, a 200x reportability
  tier above the 100x floor, a known-low-capture exon asset derived from the normals, read-level
  limits from fastp, and an explicit verdict (`PASS` / `PASS WITH LIMITATIONS` / `REVIEW`).
- **Cohort variant panel-of-normals blacklist** built from the 48 capture normals
  (`tools/build_variant_pon_blacklist.py`): 1,602 automatically derived entries across four tiers,
  with hotspot residues exempt. Recurrent artefacts that previously reached the clinical table are
  now filtered.
- Coding synonymous variants are reportable and tagged rather than dropped; ClinVar
  benign / likely-benign calls are demoted unless at a hotspot; blacklisted calls have their own
  report tab with reason and evidence.

### Changed

- **Hardening**: samplesheet validation before any task is scheduled; `pipefail` on every task
  shell; a BAM integrity check on the final alignment; ANNOVAR failures and missing databases are
  fatal, with an explicit escape flag.
- **Determinism**: `PERL_HASH_SEED=0` and `PERL_PERTURB_KEYS=0` for VEP, making its output
  byte-reproducible across runs.
- **COSMIC identifiers** are taken from VEP's `Existing_variation`; the ANNOVAR `cosmic103` table
  carries occurrence counts, not identifiers.
- **Caller thresholds moved out of the site profile.** `ext.min_var_freq` for VarScan now lives in
  `conf/modules.config`, which both sites load. A clinically meaningful threshold in a site profile
  had produced different variant sets on the two hosts.
- Legacy CNV modules retired from the DAG (z-score, concordance, annotated tables, the old CNV
  clinical report); `clinical/cnv/` is the only copy-number deliverable.
- README rewritten for this release; `docs/INSTALL.md`, `docs/deployment.md` and `docs/testing.md`
  are retained as historical records of the pre-containerisation layout.

### Fixed

- **ANNOVAR / VEP merge key**: differing indel representation left roughly one row in eight without
  caller attribution and stripped ClinVar and COSMIC from indels. Keys are now built from the
  `table_annovar` `-vcfinput` columns; orphan rows went to zero.
- **ALT-aware alignment**: the bwa-mem2 index was missing its `.alt` file, producing MAPQ-0
  alignments at paralogous loci.
- **CSF3R misannotation** from VEP `--pick` selecting a neighbouring gene's transcript.
- **reconCNV in the container**: missing `libtiff.so.5` for PIL via bokeh, fixed in image v1.1.
- **`nextflow config` on the container profile**: a closure in `conf/containers.config` resolved at
  run time but broke static config inspection; replaced with literal strings.
- **PBS resource requests**: `clusterOptions` suppressed Nextflow's own `-l select=` line, so tasks
  ran with the queue default and were killed.
- U2AF1 rescue, FLT3 tab IGV links, report column widths and several dashboard layout defects.

### Known findings

- **PURPLE segmentation depends on the C library.** AMBER and COBALT outputs are byte-identical
  across hosts, but the PCF step returns a slightly different segment set between an el9 host and
  the Ubuntu 22.04 image, with purity and ploidy unchanged and copy numbers shifted by about 0.005.
  The image, not the host, is therefore the reference for regression.
- **reconCNV** writes a placeholder HTML on failure rather than failing the run; it is a QC view.
- **FLT3_ITD_EXT** does not write `final_FLT3_ITD.vcf`; its directory output is optional and the
  other three detectors carry the ensemble.
- **17p haplotype phasing (MoChA)** was built and evaluated end to end, then parked: the panel's
  17p SNP spacing leaves phase between consecutive informative sites near random. The container
  and inputs are retained.

### Validation

- Eight-sample Twist validation cohort on the frozen image: 451 tasks, no failures, 2 h 33 min.
- Image-to-image regression: 1,233 files identical; every clinical, consensus, PURPLE and BAF
  output identical (`docs/audit/2026-09-11/run8_v1_vs_v11.md`).
- Cross-host regression, development host against clinical HPC on the same image: clinical tables
  identical on all eight samples, BAM records byte-identical, remaining differences confined to
  timestamped logs and files embedding a creation time
  (`docs/audit/2026-09-11/run8_gandalf_vs_clinical23_v2.md`).

### Deferred to 1.1

Re-run of the 48 normals through the current pipeline with a blacklist and `baf_background`
rebuild; BAF segmentation with a beta-binomial detector; female normals re-capture and a female
panel of normals; capture conformity gate; asset reconciliation; ClinVar refresh; FLT3_ITD_EXT
final VCF; per-run calibration of the 17p window depth.

## [0.1.0-dev] — 2026-05-19

The pre-1.0 working line, superseded by 1.0.0. Recorded here as the state at the end of the
initial port from the Python orchestrator.
"""

CL_MARKER = "## [1.0.0] — 2026-09-10"

CL_LINK_OLD = "[Unreleased]: https://github.com/patkarlab/nf-core-tspipe/compare/HEAD...HEAD"

CL_LINK_NEW = """[Unreleased]: https://github.com/patkarlab/nf-core-tspipe/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/patkarlab/nf-core-tspipe/releases/tag/v1.0.0"""


# ---------------------------------------------------------------------------
# Machinery
# ---------------------------------------------------------------------------

def plan_edit(root, relpath, marker, pairs):
    """
    Return (relpath, new_text) or None when the marker is already present.
    pairs is a list of (old, new); every old must appear exactly once.
    Raises SystemExit on a missing or ambiguous anchor.
    """
    path = root / relpath
    if not path.is_file():
        raise SystemExit("[error] missing file: %s" % relpath)
    text = path.read_text(encoding="utf-8")

    if marker in text:
        print("[skip]   %s (marker already present)" % relpath)
        return None

    for old, new in pairs:
        count = text.count(old)
        if count != 1:
            raise SystemExit(
                "[error] %s: anchor found %d times, expected exactly 1:\n---\n%s\n---"
                % (relpath, count, old[:200])
            )
        text = text.replace(old, new, 1)

    print("[patch]  %s (%d edit%s)" % (relpath, len(pairs), "" if len(pairs) == 1 else "s"))
    return (relpath, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "main.nf").is_file():
        raise SystemExit("[error] %s does not look like the repo root (no main.nf)" % root)

    planned = []
    for item in (
        plan_edit(root, "nextflow.config", NF_MARKER, [(NF_OLD, NF_NEW)]),
        plan_edit(root, "docs/RELEASE_NOTES.md", RN_MARKER, [(RN_OLD, RN_NEW)]),
        plan_edit(root, "CHANGELOG.md", CL_MARKER,
                  [(CL_OLD, CL_NEW), (CL_LINK_OLD, CL_LINK_NEW)]),
    ):
        if item:
            planned.append(item)

    if not planned:
        print("\nNothing to do; all three edits are already in place.")
        return 0

    if not args.apply:
        print("\nDry run. %d file(s) would change. Re-run with --apply to write."
              % len(planned))
        return 0

    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    for relpath, new_text in planned:
        path = root / relpath
        backup = path.with_name(path.name + ".bak_%s_%s" % (TAG, stamp))
        shutil.copy2(path, backup)
        print("[backup] %s" % backup.name)
        path.write_text(new_text, encoding="utf-8")
        print("[write]  %s" % relpath)

    print("\nApplied %d file(s). Verify with: git diff --stat" % len(planned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
