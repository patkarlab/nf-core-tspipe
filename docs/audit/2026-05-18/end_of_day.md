# 2026-05-18 — End-of-day summary

## Result
16/16 fresh-from-FASTQ samples through full pipeline.

Run: /goast/hemat_data/nfcore_runs/run_20260518_201435/
- 0 symlinks in clinical/ trees
- 16/16 real BAMs (1.3-1.4 GB each, link count = 1)
- 16/16 clinical final TSVs (13-39 variants per sample)
- 21 GB total deliverable size

Samples: 25NGS1307, 25NGS1358, 25NGS1586R, 25NGS1860, 25NGS1898, 25NGS980, 25RSEQ342, 25RSEQ359, 26CGH124, 26CGH14, 26CGH149, 26CGH169, 26CGH238, 26CGH26, 26CGH260, 26CGH57.

## Shipped
- Parts 1-9 (f82121c): ORGANIZE_OUTPUT module, clinical tree, real VV/ONCOVI/FLT3_TO_VARIANTS modules
- Part 10 (d20f808): publishDir mode copy for clinical deliverables
- Part 11: tools/run_pipeline.sh + tools/make_samplesheet.sh

## Pipeline gotchas
1. Channel.fromPath is queue (one-shot); use Channel.value(file(...)) to broadcast.
2. publishDir mode link silently downgrades to symlink. Use mode copy for clinical.
3. screen -r mid-run sends SIGHUP to local-executor Python subprocesses (exit 129). Use setsid + disown, never reattach.
4. join(remainder: true) is symmetric; use driver-pattern with always-emitting sentinels.
5. VEP via conda run -n vep requires perl-DBI and perl-DBD-mysql installed inside vep env.

## Infrastructure fixes today
- VEP DBI: conda install -n vep -c bioconda -c conda-forge perl-dbi perl-dbd-mysql
- VV REST disk pressure: 38 GB freed via /tmp cleanup and docker volume prune
- VVTA matviews unpopulated post-crash: refreshed all 10 in dependency order
- rv-vdb crashed mid-init: recreated from clean state

## VV REST recovery procedure
Order of matview refresh (after docker compose up -d and gunicorn restart):
exon, exon_set, transcript_lengths_mv, tx_exon_aln_mv, tx_def_summary_mv, tx_exon_set_summary_mv, full_tx_aln_w_nq_cigar_mv, all_mapped_transcript_mv, current_valid_mapped_transcript_per_gene_mv, current_valid_mapped_transcript_spans_mv

Refresh each with:
docker exec rest_variantvalidator-rv-vvta-1 psql -U uta_admin -d vvta -c "REFRESH MATERIALIZED VIEW vvta_2025_02.<view>;"

## Production launch pattern
cd /goast/hemat_data/nf-core-tspipe
setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe; yes "" | ./tools/run_pipeline.sh -resume' > /tmp/relaunch_$(date +%Y%m%d_%H%M%S).log 2>&1 &
disown

Monitor via tail -f on the log. Never screen -r.

## Tomorrow infrastructure backlog
- Move /var/lib/docker from / (70 GB) to /goast (7 TB) - permanent fix for disk pressure
- Add VV REST healthcheck loop (cron every 5 min, restart gunicorn + refresh matviews on failure)
- Wrap bin/17_variant_validator.py with retry-on-timeout and circuit breaker
- Containerize VV with built-in healthchecks
- Update tools/run_pipeline.sh to use setsid natively

## Tomorrow pipeline backlog
- B1: per-caller VCF discrepancy on 25NGS1307 (3 variants missing one caller)
- B2: 69-entry annotated-tier port residual
- B4: KMT2A-PTD detection
- B5: Rescue_Note column missing
- D1: PINDEL_FLT3_FILTER (bcftools view by region)
- D2: IGV_REPORTS real implementation (currently stub)
- 25NGS1307 MEAN_BAIT_COVERAGE drift (4249x today vs 2994x yesterday)
- Containerize VV/ONCOVI/FLT3_TO_VARIANTS (currently executor=local on host)

## Run statistics from final resume
- succeeded=86, failed=10 (VV-blocked earlier), ignored=8 (FLT3_ITD_EXT soft-fails), cached=487
- peakRunning=13, peakCpus=160, peakMemory=640 GB
