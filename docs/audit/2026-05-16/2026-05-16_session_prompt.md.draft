Continuing nf-core targeted-seq pipeline porting. Physician-scientist Nikhil
at patkarlab, myeloid panel, professional tone, no emojis, Python beginner.

REPOS:
- Pre-validation script-based pipeline (REFERENCE ONLY, not production):
    /home/hemat/targeted-seq-pipeline/
    /goast/hemat_data/targeted-seq-pipeline/
- nf-core port (THE PIPELINE WE ARE BUILDING):
    /goast/hemat_data/nf-core-tspipe/  (HEAD 7e64666)
    GitHub: patkarlab/nf-core-tspipe

STATUS COMING IN:
- SomaticSeq BAM-cross-pairing bug fixed and verified end-to-end on
  6 samples last night (2 commits on top of 89db80d).
- Pipeline currently produces: trimmed -> bwa -> markdup -> bqsr ->
  abra2 -> 8 somatic callers -> SomaticSeq ensemble -> CNV (CNVkit
  + bespoke caller). All validated with 25NGS1307 at 100% PASS recall
  vs pre-validation pipeline.
- Phase 1 (annotation/report) and Phase 2 (FLT3-ITD ensemble) NOT YET
  BUILT. That is the entire scope for today.
- 2 unpushed commits on main: 3bf7eb4, 7e64666. Push tomorrow after
  Phase 2 lands.

TODAY'S OBJECTIVE:
Build Phase 2 (FLT3-ITD 3-caller ensemble) end-to-end and start Phase 1
(annotation chain). Target: FLT3 fully landed and exercised on 1 sample;
Phase 1 through ANNOVAR running.

WHAT EXISTS IN THE PORT ALREADY:
Modules with COMPLETE topology AND script body (need only a real run):
  - bam_to_flt3_fastq.nf
  - flt3_itd_ext.nf
  - variant_filter.nf  (calls bin/variant_filter.py, may not exist yet)

Modules with topology drafted, script body stubbed:
  - vep_annotate.nf  (currently bundles VEP+ANNOVAR+merge — recommend split into 3)
  - flt3_consensus.nf  (4-input tuple, MUST revise to 3)
  - flt3_to_variants.nf
  - igv_reports.nf

Modules that don't exist yet:
  - getitd.nf
  - filt3r.nf
  - annovar.nf
  - annotation_merge.nf
  - clinical_tier.nf

CONFIRMED RESOURCES (yesterday's audit):
- ANNOVAR Docker (preferred): statisticalgenetics/annovar:latest
    table_annovar.pl at /usr/bin/table_annovar.pl
- ANNOVAR humandb hg38:
    /goast/hemat_data/targeted-seq-pipeline/software/annovar/humandb
- VEP cache (release 105 GRCh38):
    /home/hemat/targeted-seq-pipeline/references/vep_cache/homo_sapiens/105_GRCh38/
- FLT3_ITD_EXT: zhkddocker/flt3_itd_ext:v1.1 (pulled)
- filt3r local install (HAS Dockerfile in-tree):
    /home/hemat/programs/filt3r/
- getITD local install (pure-Python, bundled anno/):
    /home/hemat/programs/getitd/
- Myeloid driver genes TSV: /home/hemat/targeted-seq-pipeline/references/myeloid_driver_genes.tsv
- Myeloid hotspots TSV:     /home/hemat/targeted-seq-pipeline/references/myeloid_hotspots.tsv

NO biocontainer / quay images for filt3r or getITD exist. Build locally.

REFERENCE SCRIPTS (read these BEFORE writing modules):
- scripts/09_flt3_itd.py        (driver for 3 FLT3 callers + Pindel exposure)
- scripts/09b_flt3_consensus.py (3-tool consensus rules, parsing logic)
- scripts/13_annotate.py        (VEP+ANNOVAR+merge — split into 3 modules)
- scripts/14_variant_filter.py  (clinical filter + blacklist)
- scripts/17b_flt3_to_variants.py  (FLT3 -> clinical TSV merge)
- scripts/17c_clinical_tier.py  (AMP/ASCO/CAP tier overlay)
- scripts/16_igv_reports.py
- scripts/bam_to_flt3_fastq.py

CRITICAL DECISIONS ALREADY MADE:
1. FLT3 ensemble is 3-caller: FLT3_ITD_EXT + filt3r + getITD. Pindel
   stays in the SNV/INDEL somatic ensemble only.
2. flt3_consensus.nf MUST be revised from 4-input to 3-input tuple
   (drop pindel slot). Use .join(by:0) for joining the 3 caller
   outputs — same bug shape as yesterday's SomaticSeq fix.
3. SomaticSeq caller order (from scripts/13_annotate.py:70):
   ["Mutect2", "VarScan", "VarDict", "Strelka",
    "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]
4. Clinical tier needs a per-sample diagnosis context (default AML).
   Add a 'dx' column to the samplesheet.

CRITICAL PORT HABITS (FROM YESTERDAY'S BUG):
- When a process needs 2+ meta-keyed channels, .join(by:0) them in the
  workflow. NEVER pass two meta-keyed queue channels positionally.
- Underscore-prefixed unused vars in process inputs are a red flag.
  Don't silence linter warnings; ask why the arg is there.
- Use git commit -F file.txt, not -m "..." for multi-paragraph messages
  (terminal paste-wrap mangles them).
- For verification of meta-key joins: compare task tag (from output dir
  name) vs staged data identity (e.g., samtools view -H), NOT
  staged-file basename vs staged-file metadata (tautological).

OPERATIONAL CONTEXT:
- gandalf hardware: 192 cores, 1.5 TB RAM
- Current nextflow profile limits to executor cpus=16, memory=64GB,
  queueSize=8 — actually fine, 6-sample SomaticSeq ran in 35 min.
- Daemon screen pattern: screen -dmS <name> bash -c '... > log 2>&1'
- Pre-flight: rm -f /goast/hemat_data/nf-core-tspipe/.nextflow/cache/*/db/LOCK
- Python str_replace for patches (not sed)
- Multi-line commit msgs: cat to /tmp/msg.txt + git commit -F
- Triple-click code blocks for paste, one command at a time

ORDER OF ATTACK FOR TODAY (do NOT improvise):
1. Push 2 unpushed commits (3bf7eb4, 7e64666) to origin so the work
   is safe.
2. Real-run validation of completed FLT3 modules (bam_to_flt3_fastq +
   flt3_itd_ext) on a single sample (25NGS1307 preferred).
3. Decide FLT3 region width:
   - current bam_to_flt3_fastq.nf:  chr13:28033000-28036000 (3kb)
   - pre-validation script:          chr13:28003000-28101000 (98kb)
   Widen to match unless we have a reason not to.
4. Build getITD container OR mount-local-install pattern (CNVKit-style).
5. Build filt3r container from /home/hemat/programs/filt3r/Dockerfile.
6. Write getitd.nf + filt3r.nf modules.
7. Revise flt3_consensus.nf: 4-input -> 3-input tuple. Port the
   consensus logic from 09b_flt3_consensus.py into bin/flt3_consensus.py.
8. Wire 5 FLT3 modules into subworkflows/local/flt3_itd.nf. Uncomment
   FLT3_ITD(...) at workflows/tspipe.nf:146 USING .join(by:0).
9. Stub-mode validation of the FLT3 subworkflow (DAG correctness).
10. Real-mode run on 1 sample with known FLT3-ITD status (need Nikhil
    to nominate which sample to use as the validation gate — likely
    one of yesterday's batch that is FLT3-ITD positive in clinical
    record).
11. If time: start Phase 1 by splitting vep_annotate.nf into vep.nf,
    annovar.nf, annotation_merge.nf. Use statisticalgenetics/annovar
    for the ANNOVAR module. Stub-mode validate.

FILES IN /tmp THAT MAY OR MAY NOT SURVIVE OVERNIGHT:
- /tmp/2026-05-15_session_notes_actual.md (also at:
  /goast/hemat_data/nf-core-tspipe/2026-05-15_session_notes_actual.md.draft)
- /tmp/apply_somaticseq_bam_join.py
- /tmp/nfcore_batch_6samples/  (6 samples' published somaticseq outputs)
- /tmp/cnv_wiring/batch_6samples.csv  (samplesheet)
- /tmp/cnv_wiring/batch_6samples_bamfix_20260515_190817.log  (run log)

If any of these are gone tomorrow, they can be regenerated from the
nf-core run cache (work/ dir is on /goast and persists).

START SESSION BY:
1. Confirming git status: cd /goast/hemat_data/nf-core-tspipe && git log -3
2. Pushing 3bf7eb4 and 7e64666 to origin
3. Reading scripts/09_flt3_itd.py and scripts/09b_flt3_consensus.py
   IN FULL before writing any modules.
4. Picking up at "Order of attack" step 2.
