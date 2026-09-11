# Run comparison: gandalf (/goast/hemat_data/twist_val/tspipe_run8_img11) vs clinical23 (/goast/hemat_data/twist_val/tspipe_run8_c23) -- 2026-09-11

Files: 1386 common, 9 only in gandalf, 1 only in clinical23. Common: 1225 identical (md5), 161 differ (37 real text differences, 23 cosmetic-only text differences, 101 binary/other).

Cosmetic = the differing lines match after masking paths, dates, run names, session ids and task hashes.

| Top-level dir | identical | real diff | cosmetic diff | binary diff |
|---|---|---|---|---|
| 26CGH1043-TwistMyVal | 154 | 6 | 2 | 13 |
| 26CGH1250-TwistMyVal | 162 | 5 | 3 | 13 |
| 26CGH1292-TwistMyVal | 146 | 5 | 3 | 13 |
| 26CGH132-TwistMyVal | 146 | 4 | 3 | 12 |
| 26CGH1480-TwistMyVal | 152 | 5 | 3 | 13 |
| 26CGH60-TwistMyVal | 148 | 4 | 3 | 12 |
| 26CGH799-TwistMyVal | 152 | 4 | 3 | 12 |
| 26CGH885-TwistMyVal | 152 | 4 | 3 | 12 |
| assets | 13 | 0 | 0 | 0 |
| cohort_index.html | 0 | 0 | 0 | 1 |

## Real text differences (37)

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_genebe_cache.json

lines gandalf=98, clinical23=1; only-in-gandalf 98, only-in-clinical23 1

- A: `{`
- A: `  "chr13:28034141:T:C": {`
- A: `    "_fetched_at": "2026-09-11 06:27 UTC",`
- A: `    "acmg_classification": "Uncertain_significance",`
- A: `    "acmg_criteria": "PM2",`
- B: `{}`

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:14:48 GMT 2026`
- B: `# Started on: Fri Sep 11 02:42:33 GMT 2026`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:37:38.397 [INFO ] Amber version 4.3`
- A: `15:37:41.169 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:37:41.911 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:37:41.912 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:37:43.740 [INFO ] applying PCF segmentation`
- B: `02:53:19.166 [INFO ] Amber version 4.3`
- B: `02:53:22.140 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:53:22.616 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:53:22.616 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:53:25.482 [INFO ] applying PCF segmentation`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:37:44.887 [INFO ] Cobalt version 3.0`
- A: `15:37:44.892 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:37:45.012 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- A: `15:37:52.472 [INFO ] tumor depths(3088257) collected`
- A: `15:37:53.490 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:55:17.819 [INFO ] Cobalt version 3.0`
- B: `02:55:17.825 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:55:17.975 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- B: `02:55:25.051 [INFO ] tumor depths(3088257) collected`
- B: `02:55:26.362 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:52:05.095 [INFO ] Purple version 4.4`
- A: `15:52:05.099 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- A: `15:52:05.099 [INFO ] output directory: purple/`
- A: `15:52:05.171 [INFO ] using ref genome: V38`
- A: `15:52:07.250 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `02:59:51.614 [INFO ] Purple version 4.4`
- B: `02:59:51.619 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- B: `02:59:51.619 [INFO ] output directory: purple/`
- B: `02:59:51.730 [INFO ] using ref genome: V38`
- B: `02:59:53.193 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1043-TwistMyVal/qc/26CGH1043-TwistMyVal.quickcheck.txt

lines gandalf=2, clinical23=2; only-in-gandalf 1, only-in-clinical23 1

- A: `OK 26CGH1043-TwistMyVal.final.bam (2810440112 bytes)`
- B: `OK 26CGH1043-TwistMyVal.final.bam (2810440113 bytes)`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:16:30 GMT 2026`
- B: `# Started on: Fri Sep 11 02:46:07 GMT 2026`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:42:40.140 [INFO ] Amber version 4.3`
- A: `15:42:42.847 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:42:43.274 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:42:43.274 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:42:45.138 [INFO ] applying PCF segmentation`
- B: `02:58:27.249 [INFO ] Amber version 4.3`
- B: `02:58:30.273 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:58:30.746 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:58:30.747 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:58:33.608 [INFO ] applying PCF segmentation`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:42:46.215 [INFO ] Cobalt version 3.0`
- A: `15:42:46.220 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:42:46.340 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- A: `15:42:53.154 [INFO ] tumor depths(3088257) collected`
- A: `15:42:54.479 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:56:27.437 [INFO ] Cobalt version 3.0`
- B: `02:56:27.442 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:56:27.597 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- B: `02:56:35.184 [INFO ] tumor depths(3088257) collected`
- B: `02:56:36.548 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:52:33.100 [INFO ] Purple version 4.4`
- A: `15:52:33.104 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- A: `15:52:33.104 [INFO ] output directory: purple/`
- A: `15:52:33.178 [INFO ] using ref genome: V38`
- A: `15:52:34.428 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `03:06:19.242 [INFO ] Purple version 4.4`
- B: `03:06:19.247 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- B: `03:06:19.247 [INFO ] output directory: purple/`
- B: `03:06:19.363 [INFO ] using ref genome: V38`
- B: `03:06:20.861 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1250-TwistMyVal/qc/26CGH1250-TwistMyVal.quickcheck.txt

lines gandalf=2, clinical23=2; only-in-gandalf 1, only-in-clinical23 1

- A: `OK 26CGH1250-TwistMyVal.final.bam (3066024467 bytes)`
- B: `OK 26CGH1250-TwistMyVal.final.bam (3066024468 bytes)`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:16:43 GMT 2026`
- B: `# Started on: Fri Sep 11 02:44:05 GMT 2026`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:47:52.652 [INFO ] Amber version 4.3`
- A: `15:47:55.978 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:47:56.416 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:47:56.417 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:47:58.549 [INFO ] applying PCF segmentation`
- B: `02:54:55.318 [INFO ] Amber version 4.3`
- B: `02:54:58.299 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:54:58.781 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:54:58.782 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:55:01.741 [INFO ] applying PCF segmentation`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:47:59.830 [INFO ] Cobalt version 3.0`
- A: `15:47:59.835 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:47:59.973 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- A: `15:48:05.181 [INFO ] tumor depths(3088257) collected`
- A: `15:48:06.359 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:43:45.448 [INFO ] Cobalt version 3.0`
- B: `02:43:45.455 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:43:45.608 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- B: `02:43:52.999 [INFO ] tumor depths(3088257) collected`
- B: `02:43:54.368 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:52:39.253 [INFO ] Purple version 4.4`
- A: `15:52:39.257 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- A: `15:52:39.257 [INFO ] output directory: purple/`
- A: `15:52:39.328 [INFO ] using ref genome: V38`
- A: `15:52:40.538 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `02:56:47.323 [INFO ] Purple version 4.4`
- B: `02:56:47.328 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- B: `02:56:47.328 [INFO ] output directory: purple/`
- B: `02:56:47.416 [INFO ] using ref genome: V38`
- B: `02:56:48.855 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1292-TwistMyVal/qc/26CGH1292-TwistMyVal.quickcheck.txt

lines gandalf=2, clinical23=2; only-in-gandalf 1, only-in-clinical23 1

- A: `OK 26CGH1292-TwistMyVal.final.bam (3103373433 bytes)`
- B: `OK 26CGH1292-TwistMyVal.final.bam (3103373434 bytes)`

### 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:17:03 GMT 2026`
- B: `# Started on: Fri Sep 11 03:06:46 GMT 2026`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:24:39.968 [INFO ] Amber version 4.3`
- A: `15:24:43.363 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:24:43.820 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:24:43.820 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:24:45.649 [INFO ] applying PCF segmentation`
- B: `03:09:00.578 [INFO ] Amber version 4.3`
- B: `03:09:03.612 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `03:09:04.068 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `03:09:04.069 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `03:09:06.964 [INFO ] applying PCF segmentation`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:24:46.846 [INFO ] Cobalt version 3.0`
- A: `15:24:46.851 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:24:47.002 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- A: `15:24:52.999 [INFO ] tumor depths(3088257) collected`
- A: `15:24:54.736 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `03:01:40.075 [INFO ] Cobalt version 3.0`
- B: `03:01:40.081 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `03:01:40.260 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- B: `03:01:48.046 [INFO ] tumor depths(3088257) collected`
- B: `03:01:49.423 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:49:58.763 [INFO ] Purple version 4.4`
- A: `15:49:58.766 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- A: `15:49:58.766 [INFO ] output directory: purple/`
- A: `15:49:58.840 [INFO ] using ref genome: V38`
- A: `15:50:00.082 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `03:18:11.773 [INFO ] Purple version 4.4`
- B: `03:18:11.778 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- B: `03:18:11.778 [INFO ] output directory: purple/`
- B: `03:18:11.871 [INFO ] using ref genome: V38`
- B: `03:18:13.388 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:14:44 GMT 2026`
- B: `# Started on: Fri Sep 11 02:36:20 GMT 2026`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:31:47.904 [INFO ] Amber version 4.3`
- A: `15:31:51.089 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:31:51.665 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:31:51.666 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:31:53.801 [INFO ] applying PCF segmentation`
- B: `02:42:54.508 [INFO ] Amber version 4.3`
- B: `02:42:57.529 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:42:58.043 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:42:58.043 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:43:00.860 [INFO ] applying PCF segmentation`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:31:31.011 [INFO ] Cobalt version 3.0`
- A: `15:31:31.016 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:31:31.141 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- A: `15:31:36.198 [INFO ] tumor depths(3088257) collected`
- A: `15:31:38.099 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:48:26.099 [INFO ] Cobalt version 3.0`
- B: `02:48:26.105 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:48:26.257 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- B: `02:48:32.564 [INFO ] tumor depths(3088257) collected`
- B: `02:48:33.839 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:51:55.806 [INFO ] Purple version 4.4`
- A: `15:51:55.810 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- A: `15:51:55.810 [INFO ] output directory: purple/`
- A: `15:51:55.883 [INFO ] using ref genome: V38`
- A: `15:51:57.135 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `02:54:01.419 [INFO ] Purple version 4.4`
- B: `02:54:01.423 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- B: `02:54:01.424 [INFO ] output directory: purple/`
- B: `02:54:01.523 [INFO ] using ref genome: V38`
- B: `02:54:03.045 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1480-TwistMyVal/qc/26CGH1480-TwistMyVal.quickcheck.txt

lines gandalf=2, clinical23=2; only-in-gandalf 1, only-in-clinical23 1

- A: `OK 26CGH1480-TwistMyVal.final.bam (2687658698 bytes)`
- B: `OK 26CGH1480-TwistMyVal.final.bam (2687658699 bytes)`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:49:34 GMT 2026`
- B: `# Started on: Fri Sep 11 02:37:30 GMT 2026`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:57:21.609 [INFO ] Amber version 4.3`
- A: `15:57:24.407 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:57:25.416 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:57:25.417 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:57:27.423 [INFO ] applying PCF segmentation`
- B: `02:59:40.955 [INFO ] Amber version 4.3`
- B: `02:59:44.022 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:59:44.512 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:59:44.513 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:59:47.627 [INFO ] applying PCF segmentation`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:57:28.646 [INFO ] Cobalt version 3.0`
- A: `15:57:28.652 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:57:28.803 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- A: `15:57:34.796 [INFO ] tumor depths(3088257) collected`
- A: `15:57:35.803 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:38:30.533 [INFO ] Cobalt version 3.0`
- B: `02:38:30.539 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:38:30.676 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- B: `02:38:38.571 [INFO ] tumor depths(3088257) collected`
- B: `02:38:39.882 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:58:58.214 [INFO ] Purple version 4.4`
- A: `15:58:58.218 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- A: `15:58:58.218 [INFO ] output directory: purple/`
- A: `15:58:58.292 [INFO ] using ref genome: V38`
- A: `15:58:59.584 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `03:03:39.333 [INFO ] Purple version 4.4`
- B: `03:03:39.338 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- B: `03:03:39.339 [INFO ] output directory: purple/`
- B: `03:03:39.426 [INFO ] using ref genome: V38`
- B: `03:03:40.954 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 14:49:25 GMT 2026`
- B: `# Started on: Fri Sep 11 02:33:58 GMT 2026`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `15:13:41.844 [INFO ] Amber version 4.3`
- A: `15:13:45.188 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:13:45.636 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:13:45.637 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:13:47.677 [INFO ] applying PCF segmentation`
- B: `02:36:57.574 [INFO ] Amber version 4.3`
- B: `02:37:00.658 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:37:01.140 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:37:01.140 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:37:03.967 [INFO ] applying PCF segmentation`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `15:13:49.071 [INFO ] Cobalt version 3.0`
- A: `15:13:49.076 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:13:49.229 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- A: `15:13:56.012 [INFO ] tumor depths(3088257) collected`
- A: `15:13:57.319 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:25:30.157 [INFO ] Cobalt version 3.0`
- B: `02:25:30.163 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:25:30.359 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- B: `02:25:36.803 [INFO ] tumor depths(3088257) collected`
- B: `02:25:38.160 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `15:18:45.569 [INFO ] Purple version 4.4`
- A: `15:18:45.573 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- A: `15:18:45.573 [INFO ] output directory: purple/`
- A: `15:18:45.662 [INFO ] using ref genome: V38`
- A: `15:18:47.667 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `02:44:15.114 [INFO ] Purple version 4.4`
- B: `02:44:15.119 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- B: `02:44:15.119 [INFO ] output directory: purple/`
- B: `02:44:15.228 [INFO ] using ref genome: V38`
- B: `02:44:16.772 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 14:38:29 GMT 2026`
- B: `# Started on: Fri Sep 11 02:40:40 GMT 2026`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.amber.log

lines gandalf=6, clinical23=6; only-in-gandalf 6, only-in-clinical23 6

- A: `14:45:20.294 [INFO ] Amber version 4.3`
- A: `14:45:23.801 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `14:45:24.222 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `14:45:24.223 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `14:45:26.204 [INFO ] applying PCF segmentation`
- B: `02:41:28.765 [INFO ] Amber version 4.3`
- B: `02:41:31.774 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `02:41:32.262 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `02:41:32.262 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `02:41:35.289 [INFO ] applying PCF segmentation`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.cobalt.log

lines gandalf=7, clinical23=7; only-in-gandalf 7, only-in-clinical23 7

- A: `14:45:27.250 [INFO ] Cobalt version 3.0`
- A: `14:45:27.255 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `14:45:27.378 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- A: `14:45:33.058 [INFO ] tumor depths(3088257) collected`
- A: `14:45:34.192 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `02:34:57.181 [INFO ] Cobalt version 3.0`
- B: `02:34:57.187 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `02:34:57.343 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- B: `02:35:03.932 [INFO ] tumor depths(3088257) collected`
- B: `02:35:05.278 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.purple.log

lines gandalf=19, clinical23=19; only-in-gandalf 19, only-in-clinical23 19

- A: `14:50:19.067 [INFO ] Purple version 4.4`
- A: `14:50:19.071 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- A: `14:50:19.071 [INFO ] output directory: purple/`
- A: `14:50:19.162 [INFO ] using ref genome: V38`
- A: `14:50:21.299 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `02:45:47.730 [INFO ] Purple version 4.4`
- B: `02:45:47.734 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- B: `02:45:47.734 [INFO ] output directory: purple/`
- B: `02:45:47.840 [INFO ] using ref genome: V38`
- B: `02:45:49.359 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

## Cosmetic-only differences (23)

- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1043-TwistMyVal_R1.fastq.gz -I 26CGH1043-TwistMyVal_R2.fastq.gz -o 26CGH1043-TwistMyVal_trim_R1.fastq.gz -O 26CGH1043-TwistMyVal_trim`)
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_mobidetails_cache.json (only-in-gandalf 6, only-in-clinical23 6; e.g. `    "_fetched_at": "2026-09-11 06:27 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1250-TwistMyVal_R1.fastq.gz -I 26CGH1250-TwistMyVal_R2.fastq.gz -o 26CGH1250-TwistMyVal_trim_R1.fastq.gz -O 26CGH1250-TwistMyVal_trim`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_genebe_cache.json (only-in-gandalf 5, only-in-clinical23 5; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_mobidetails_cache.json (only-in-gandalf 5, only-in-clinical23 5; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1292-TwistMyVal_R1.fastq.gz -I 26CGH1292-TwistMyVal_R2.fastq.gz -o 26CGH1292-TwistMyVal_trim_R1.fastq.gz -O 26CGH1292-TwistMyVal_trim`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_genebe_cache.json (only-in-gandalf 7, only-in-clinical23 7; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_mobidetails_cache.json (only-in-gandalf 7, only-in-clinical23 7; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH132-TwistMyVal_R1.fastq.gz -I 26CGH132-TwistMyVal_R2.fastq.gz -o 26CGH132-TwistMyVal_trim_R1.fastq.gz -O 26CGH132-TwistMyVal_trim_R2.`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_genebe_cache.json (only-in-gandalf 10, only-in-clinical23 10; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_mobidetails_cache.json (only-in-gandalf 10, only-in-clinical23 10; e.g. `    "_fetched_at": "2026-09-11 06:28 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1480-TwistMyVal_R1.fastq.gz -I 26CGH1480-TwistMyVal_R2.fastq.gz -o 26CGH1480-TwistMyVal_trim_R1.fastq.gz -O 26CGH1480-TwistMyVal_trim`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_genebe_cache.json (only-in-gandalf 17, only-in-clinical23 17; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_mobidetails_cache.json (only-in-gandalf 17, only-in-clinical23 17; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH60-TwistMyVal_R1.fastq.gz -I 26CGH60-TwistMyVal_R2.fastq.gz -o 26CGH60-TwistMyVal_trim_R1.fastq.gz -O 26CGH60-TwistMyVal_trim_R2.fast`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_genebe_cache.json (only-in-gandalf 5, only-in-clinical23 5; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_mobidetails_cache.json (only-in-gandalf 5, only-in-clinical23 5; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH799-TwistMyVal_R1.fastq.gz -I 26CGH799-TwistMyVal_R2.fastq.gz -o 26CGH799-TwistMyVal_trim_R1.fastq.gz -O 26CGH799-TwistMyVal_trim_R2.`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_genebe_cache.json (only-in-gandalf 7, only-in-clinical23 7; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_mobidetails_cache.json (only-in-gandalf 7, only-in-clinical23 7; e.g. `    "_fetched_at": "2026-09-11 06:29 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH885-TwistMyVal_R1.fastq.gz -I 26CGH885-TwistMyVal_R2.fastq.gz -o 26CGH885-TwistMyVal_trim_R1.fastq.gz -O 26CGH885-TwistMyVal_trim_R2.`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_genebe_cache.json (only-in-gandalf 9, only-in-clinical23 9; e.g. `    "_fetched_at": "2026-09-11 06:30 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_mobidetails_cache.json (only-in-gandalf 9, only-in-clinical23 9; e.g. `    "_fetched_at": "2026-09-11 06:30 UTC",`)

## Binary / other files that differ by md5 (101)

- 26CGH1043-TwistMyVal/26CGH1043-TwistMyVal_report.zip
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.final.bam
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.final.bam.bai
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_fastp.html
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_igv_report.html
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_report.html
- 26CGH1043-TwistMyVal/clinical/cnv/reconcnv/26CGH1043-TwistMyVal.reconcnv.html
- 26CGH1043-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1043-TwistMyVal.reconcnv.html
- 26CGH1043-TwistMyVal/purecn/26CGH1043-TwistMyVal.pdf
- 26CGH1043-TwistMyVal/purecn/26CGH1043-TwistMyVal.rds
- 26CGH1043-TwistMyVal/purecn/26CGH1043-TwistMyVal_chromosomes.pdf
- 26CGH1043-TwistMyVal/purecn/26CGH1043-TwistMyVal_local_optima.pdf
- 26CGH1043-TwistMyVal/purecn/26CGH1043-TwistMyVal_segmentation.pdf
- 26CGH1250-TwistMyVal/26CGH1250-TwistMyVal_report.zip
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal.final.bam
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal.final.bam.bai
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_fastp.html
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_igv_report.html
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_report.html
- 26CGH1250-TwistMyVal/clinical/cnv/reconcnv/26CGH1250-TwistMyVal.reconcnv.html
- 26CGH1250-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1250-TwistMyVal.reconcnv.html
- 26CGH1250-TwistMyVal/purecn/26CGH1250-TwistMyVal.pdf
- 26CGH1250-TwistMyVal/purecn/26CGH1250-TwistMyVal.rds
- 26CGH1250-TwistMyVal/purecn/26CGH1250-TwistMyVal_chromosomes.pdf
- 26CGH1250-TwistMyVal/purecn/26CGH1250-TwistMyVal_local_optima.pdf
- 26CGH1250-TwistMyVal/purecn/26CGH1250-TwistMyVal_segmentation.pdf
- 26CGH1292-TwistMyVal/26CGH1292-TwistMyVal_report.zip
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal.final.bam
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal.final.bam.bai
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_fastp.html
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_igv_report.html
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_report.html
- 26CGH1292-TwistMyVal/clinical/cnv/reconcnv/26CGH1292-TwistMyVal.reconcnv.html
- 26CGH1292-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1292-TwistMyVal.reconcnv.html
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal.rds
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_chromosomes.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_local_optima.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_segmentation.pdf
- 26CGH132-TwistMyVal/26CGH132-TwistMyVal_report.zip
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal.final.bam
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_fastp.html
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_igv_report.html
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_report.html
- 26CGH132-TwistMyVal/clinical/cnv/reconcnv/26CGH132-TwistMyVal.reconcnv.html
- 26CGH132-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH132-TwistMyVal.reconcnv.html
- 26CGH132-TwistMyVal/purecn/26CGH132-TwistMyVal.pdf
- 26CGH132-TwistMyVal/purecn/26CGH132-TwistMyVal.rds
- 26CGH132-TwistMyVal/purecn/26CGH132-TwistMyVal_chromosomes.pdf
- 26CGH132-TwistMyVal/purecn/26CGH132-TwistMyVal_local_optima.pdf
- 26CGH132-TwistMyVal/purecn/26CGH132-TwistMyVal_segmentation.pdf
- 26CGH1480-TwistMyVal/26CGH1480-TwistMyVal_report.zip
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal.final.bam
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal.final.bam.bai
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_fastp.html
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_igv_report.html
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_report.html
- 26CGH1480-TwistMyVal/clinical/cnv/reconcnv/26CGH1480-TwistMyVal.reconcnv.html
- 26CGH1480-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1480-TwistMyVal.reconcnv.html
- 26CGH1480-TwistMyVal/purecn/26CGH1480-TwistMyVal.pdf
- 26CGH1480-TwistMyVal/purecn/26CGH1480-TwistMyVal.rds
- 26CGH1480-TwistMyVal/purecn/26CGH1480-TwistMyVal_chromosomes.pdf
- 26CGH1480-TwistMyVal/purecn/26CGH1480-TwistMyVal_local_optima.pdf
- 26CGH1480-TwistMyVal/purecn/26CGH1480-TwistMyVal_segmentation.pdf
- 26CGH60-TwistMyVal/26CGH60-TwistMyVal_report.zip
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal.final.bam
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_fastp.html
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_igv_report.html
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_report.html
- 26CGH60-TwistMyVal/clinical/cnv/reconcnv/26CGH60-TwistMyVal.reconcnv.html
- 26CGH60-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH60-TwistMyVal.reconcnv.html
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal.rds
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_chromosomes.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_local_optima.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_segmentation.pdf
- 26CGH799-TwistMyVal/26CGH799-TwistMyVal_report.zip
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal.final.bam
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_fastp.html
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_igv_report.html
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_report.html
- 26CGH799-TwistMyVal/clinical/cnv/reconcnv/26CGH799-TwistMyVal.reconcnv.html
- 26CGH799-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH799-TwistMyVal.reconcnv.html
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal.rds
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_chromosomes.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_local_optima.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_segmentation.pdf
- 26CGH885-TwistMyVal/26CGH885-TwistMyVal_report.zip
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal.final.bam
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_fastp.html
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_igv_report.html
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_report.html
- 26CGH885-TwistMyVal/clinical/cnv/reconcnv/26CGH885-TwistMyVal.reconcnv.html
- 26CGH885-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH885-TwistMyVal.reconcnv.html
- 26CGH885-TwistMyVal/purecn/26CGH885-TwistMyVal.pdf
- 26CGH885-TwistMyVal/purecn/26CGH885-TwistMyVal.rds
- 26CGH885-TwistMyVal/purecn/26CGH885-TwistMyVal_chromosomes.pdf
- 26CGH885-TwistMyVal/purecn/26CGH885-TwistMyVal_local_optima.pdf
- 26CGH885-TwistMyVal/purecn/26CGH885-TwistMyVal_segmentation.pdf
- cohort_index.html

## Present on one side only

- only gandalf: 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_oncokb_cache.json
- only gandalf: 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_oncokb_cache.json
- only gandalf: tspipe_run8_img11_reports.zip
- only clinical23: tspipe_run8_c23_reports.zip

