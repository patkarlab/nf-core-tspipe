# Run comparison: v1 (/goast/hemat_data/twist_val/tspipe_run8_img) vs v1.1 (/goast/hemat_data/twist_val/tspipe_run8_img11) -- 2026-09-11

Files: 1394 common, 1 only in v1, 1 only in v1.1. Common: 1233 identical (md5), 161 differ (48 real text differences, 24 cosmetic-only text differences, 89 binary/other).

Cosmetic = the differing lines match after masking paths, dates, run names, session ids and task hashes.

| Top-level dir | identical | real diff | cosmetic diff | binary diff |
|---|---|---|---|---|
| 26CGH1043-TwistMyVal | 156 | 6 | 3 | 11 |
| 26CGH1250-TwistMyVal | 164 | 6 | 3 | 11 |
| 26CGH1292-TwistMyVal | 148 | 6 | 3 | 11 |
| 26CGH132-TwistMyVal | 146 | 6 | 3 | 11 |
| 26CGH1480-TwistMyVal | 154 | 6 | 3 | 11 |
| 26CGH60-TwistMyVal | 148 | 6 | 3 | 11 |
| 26CGH799-TwistMyVal | 152 | 6 | 3 | 11 |
| 26CGH885-TwistMyVal | 152 | 6 | 3 | 11 |
| assets | 13 | 0 | 0 | 0 |
| cohort_index.html | 0 | 0 | 0 | 1 |

## Real text differences (48)

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:27:18 GMT 2026`
- B: `# Started on: Thu Sep 10 15:14:48 GMT 2026`

### 26CGH1043-TwistMyVal/clinical/cnv/reconcnv/26CGH1043-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1043-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1043-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.amber.log

lines v1=6, v1.1=6; only-in-v1 6, only-in-v1.1 6

- A: `11:35:17.508 [INFO ] Amber version 4.3`
- A: `11:35:21.002 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:35:21.644 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:35:21.644 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `11:35:23.881 [INFO ] applying PCF segmentation`
- B: `15:37:38.397 [INFO ] Amber version 4.3`
- B: `15:37:41.169 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:37:41.911 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:37:41.912 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:37:43.740 [INFO ] applying PCF segmentation`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `11:32:28.366 [INFO ] Cobalt version 3.0`
- A: `11:32:28.371 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:32:28.516 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- A: `11:32:34.647 [INFO ] tumor depths(3088257) collected`
- A: `11:32:35.844 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `15:37:44.887 [INFO ] Cobalt version 3.0`
- B: `15:37:44.892 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:37:45.012 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- B: `15:37:52.472 [INFO ] tumor depths(3088257) collected`
- B: `15:37:53.490 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `11:39:36.052 [INFO ] Purple version 4.4`
- A: `11:39:36.056 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- A: `11:39:36.056 [INFO ] output directory: purple/`
- A: `11:39:36.147 [INFO ] using ref genome: V38`
- A: `11:39:38.241 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:52:05.095 [INFO ] Purple version 4.4`
- B: `15:52:05.099 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- B: `15:52:05.099 [INFO ] output directory: purple/`
- B: `15:52:05.171 [INFO ] using ref genome: V38`
- B: `15:52:07.250 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:39:46 GMT 2026`
- B: `# Started on: Thu Sep 10 15:16:30 GMT 2026`

### 26CGH1250-TwistMyVal/clinical/cnv/reconcnv/26CGH1250-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1250-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1250-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.amber.log

lines v1=7, v1.1=6; only-in-v1 7, only-in-v1.1 6

- A: `[0.016s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:56:33.741 [INFO ] Amber version 4.3`
- A: `11:56:37.251 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:56:37.708 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:56:37.709 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:42:40.140 [INFO ] Amber version 4.3`
- B: `15:42:42.847 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:42:43.274 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:42:43.274 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:42:45.138 [INFO ] applying PCF segmentation`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.cobalt.log

lines v1=8, v1.1=7; only-in-v1 8, only-in-v1.1 7

- A: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:54:39.021 [INFO ] Cobalt version 3.0`
- A: `11:54:39.026 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:54:39.173 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- A: `11:54:45.716 [INFO ] tumor depths(3088257) collected`
- B: `15:42:46.215 [INFO ] Cobalt version 3.0`
- B: `15:42:46.220 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:42:46.340 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- B: `15:42:53.154 [INFO ] tumor depths(3088257) collected`
- B: `15:42:54.479 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `12:02:12.180 [INFO ] Purple version 4.4`
- A: `12:02:12.194 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- A: `12:02:12.195 [INFO ] output directory: purple/`
- A: `12:02:12.403 [INFO ] using ref genome: V38`
- A: `12:02:14.135 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:52:33.100 [INFO ] Purple version 4.4`
- B: `15:52:33.104 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- B: `15:52:33.104 [INFO ] output directory: purple/`
- B: `15:52:33.178 [INFO ] using ref genome: V38`
- B: `15:52:34.428 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:37:28 GMT 2026`
- B: `# Started on: Thu Sep 10 15:16:43 GMT 2026`

### 26CGH1292-TwistMyVal/clinical/cnv/reconcnv/26CGH1292-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1292-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1292-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.amber.log

lines v1=6, v1.1=6; only-in-v1 6, only-in-v1.1 6

- A: `11:44:55.143 [INFO ] Amber version 4.3`
- A: `11:44:58.919 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:44:59.561 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:44:59.562 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `11:45:01.936 [INFO ] applying PCF segmentation`
- B: `15:47:52.652 [INFO ] Amber version 4.3`
- B: `15:47:55.978 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:47:56.416 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:47:56.417 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:47:58.549 [INFO ] applying PCF segmentation`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `11:45:03.375 [INFO ] Cobalt version 3.0`
- A: `11:45:03.381 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:45:03.543 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- A: `11:45:09.046 [INFO ] tumor depths(3088257) collected`
- A: `11:45:10.080 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `15:47:59.830 [INFO ] Cobalt version 3.0`
- B: `15:47:59.835 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:47:59.973 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- B: `15:48:05.181 [INFO ] tumor depths(3088257) collected`
- B: `15:48:06.359 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `11:57:25.052 [INFO ] Purple version 4.4`
- A: `11:57:25.056 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- A: `11:57:25.056 [INFO ] output directory: purple/`
- A: `11:57:25.143 [INFO ] using ref genome: V38`
- A: `11:57:27.518 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:52:39.253 [INFO ] Purple version 4.4`
- B: `15:52:39.257 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- B: `15:52:39.257 [INFO ] output directory: purple/`
- B: `15:52:39.328 [INFO ] using ref genome: V38`
- B: `15:52:40.538 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 12:02:34 GMT 2026`
- B: `# Started on: Thu Sep 10 15:17:03 GMT 2026`

### 26CGH132-TwistMyVal/clinical/cnv/reconcnv/26CGH132-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH132-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH132-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.amber.log

lines v1=6, v1.1=6; only-in-v1 6, only-in-v1.1 6

- A: `12:17:18.448 [INFO ] Amber version 4.3`
- A: `12:17:21.699 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `12:17:22.404 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `12:17:22.404 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `12:17:24.553 [INFO ] applying PCF segmentation`
- B: `15:24:39.968 [INFO ] Amber version 4.3`
- B: `15:24:43.363 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:24:43.820 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:24:43.820 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:24:45.649 [INFO ] applying PCF segmentation`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `12:17:26.273 [INFO ] Cobalt version 3.0`
- A: `12:17:26.279 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `12:17:26.423 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- A: `12:17:32.382 [INFO ] tumor depths(3088257) collected`
- A: `12:17:33.384 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `15:24:46.846 [INFO ] Cobalt version 3.0`
- B: `15:24:46.851 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:24:47.002 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- B: `15:24:52.999 [INFO ] tumor depths(3088257) collected`
- B: `15:24:54.736 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `12:23:12.731 [INFO ] Purple version 4.4`
- A: `12:23:12.734 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- A: `12:23:12.734 [INFO ] output directory: purple/`
- A: `12:23:12.822 [INFO ] using ref genome: V38`
- A: `12:23:14.818 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:49:58.763 [INFO ] Purple version 4.4`
- B: `15:49:58.766 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- B: `15:49:58.766 [INFO ] output directory: purple/`
- B: `15:49:58.840 [INFO ] using ref genome: V38`
- B: `15:50:00.082 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:17:01 GMT 2026`
- B: `# Started on: Thu Sep 10 15:14:44 GMT 2026`

### 26CGH1480-TwistMyVal/clinical/cnv/reconcnv/26CGH1480-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1480-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1480-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.amber.log

lines v1=7, v1.1=6; only-in-v1 7, only-in-v1.1 6

- A: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:24:44.849 [INFO ] Amber version 4.3`
- A: `11:24:48.182 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:24:48.933 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:24:48.934 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:31:47.904 [INFO ] Amber version 4.3`
- B: `15:31:51.089 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:31:51.665 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:31:51.666 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:31:53.801 [INFO ] applying PCF segmentation`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.cobalt.log

lines v1=8, v1.1=7; only-in-v1 8, only-in-v1.1 7

- A: `[0.016s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:25:08.368 [INFO ] Cobalt version 3.0`
- A: `11:25:08.373 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:25:08.494 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- A: `11:25:13.797 [INFO ] tumor depths(3088257) collected`
- B: `15:31:31.011 [INFO ] Cobalt version 3.0`
- B: `15:31:31.016 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:31:31.141 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- B: `15:31:36.198 [INFO ] tumor depths(3088257) collected`
- B: `15:31:38.099 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `11:28:50.931 [INFO ] Purple version 4.4`
- A: `11:28:50.934 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- A: `11:28:50.934 [INFO ] output directory: purple/`
- A: `11:28:51.007 [INFO ] using ref genome: V38`
- A: `11:28:53.151 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:51:55.806 [INFO ] Purple version 4.4`
- B: `15:51:55.810 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- B: `15:51:55.810 [INFO ] output directory: purple/`
- B: `15:51:55.883 [INFO ] using ref genome: V38`
- B: `15:51:57.135 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:57:56 GMT 2026`
- B: `# Started on: Thu Sep 10 15:49:34 GMT 2026`

### 26CGH60-TwistMyVal/clinical/cnv/reconcnv/26CGH60-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH60-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH60-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.amber.log

lines v1=6, v1.1=6; only-in-v1 6, only-in-v1.1 6

- A: `12:04:46.232 [INFO ] Amber version 4.3`
- A: `12:04:49.712 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `12:04:50.345 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `12:04:50.346 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `12:04:52.563 [INFO ] applying PCF segmentation`
- B: `15:57:21.609 [INFO ] Amber version 4.3`
- B: `15:57:24.407 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:57:25.416 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:57:25.417 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:57:27.423 [INFO ] applying PCF segmentation`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `12:08:23.364 [INFO ] Cobalt version 3.0`
- A: `12:08:23.369 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `12:08:23.514 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- A: `12:08:29.766 [INFO ] tumor depths(3088257) collected`
- A: `12:08:30.764 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `15:57:28.646 [INFO ] Cobalt version 3.0`
- B: `15:57:28.652 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:57:28.803 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- B: `15:57:34.796 [INFO ] tumor depths(3088257) collected`
- B: `15:57:35.803 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `12:21:58.172 [INFO ] Purple version 4.4`
- A: `12:21:58.176 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- A: `12:21:58.176 [INFO ] output directory: purple/`
- A: `12:21:58.264 [INFO ] using ref genome: V38`
- A: `12:22:00.326 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:58:58.214 [INFO ] Purple version 4.4`
- B: `15:58:58.218 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- B: `15:58:58.218 [INFO ] output directory: purple/`
- B: `15:58:58.292 [INFO ] using ref genome: V38`
- B: `15:58:59.584 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 11:05:54 GMT 2026`
- B: `# Started on: Thu Sep 10 14:49:25 GMT 2026`

### 26CGH799-TwistMyVal/clinical/cnv/reconcnv/26CGH799-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH799-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH799-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.amber.log

lines v1=7, v1.1=6; only-in-v1 7, only-in-v1.1 6

- A: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:12:18.859 [INFO ] Amber version 4.3`
- A: `11:12:22.294 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:12:23.020 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:12:23.021 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:13:41.844 [INFO ] Amber version 4.3`
- B: `15:13:45.188 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `15:13:45.636 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `15:13:45.637 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `15:13:47.677 [INFO ] applying PCF segmentation`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `11:10:16.704 [INFO ] Cobalt version 3.0`
- A: `11:10:16.710 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:10:16.862 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- A: `11:10:22.877 [INFO ] tumor depths(3088257) collected`
- A: `11:10:24.186 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `15:13:49.071 [INFO ] Cobalt version 3.0`
- B: `15:13:49.076 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `15:13:49.229 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- B: `15:13:56.012 [INFO ] tumor depths(3088257) collected`
- B: `15:13:57.319 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.purple.log

lines v1=19, v1.1=19; only-in-v1 19, only-in-v1.1 19

- A: `11:18:58.536 [INFO ] Purple version 4.4`
- A: `11:18:58.540 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- A: `11:18:58.540 [INFO ] output directory: purple/`
- A: `11:18:58.629 [INFO ] using ref genome: V38`
- A: `11:19:00.891 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `15:18:45.569 [INFO ] Purple version 4.4`
- B: `15:18:45.573 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- B: `15:18:45.573 [INFO ] output directory: purple/`
- B: `15:18:45.662 [INFO ] using ref genome: V38`
- B: `15:18:47.667 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_hsmetrics.txt

lines v1=213, v1.1=213; only-in-v1 1, only-in-v1.1 1

- A: `# Started on: Thu Sep 10 10:55:32 GMT 2026`
- B: `# Started on: Thu Sep 10 14:38:29 GMT 2026`

### 26CGH885-TwistMyVal/clinical/cnv/reconcnv/26CGH885-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH885-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH885-TwistMyVal.reconcnv.log

lines v1=15, v1.1=1; only-in-v1 14, only-in-v1.1 0

- A: `Traceback (most recent call last):`
- A: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- A: `    from bokeh.layouts import row, column, layout`
- A: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- A: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.amber.log

lines v1=6, v1.1=6; only-in-v1 6, only-in-v1.1 6

- A: `11:00:44.658 [INFO ] Amber version 4.3`
- A: `11:00:47.808 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `11:00:48.840 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `11:00:48.841 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `11:00:50.857 [INFO ] applying PCF segmentation`
- B: `14:45:20.294 [INFO ] Amber version 4.3`
- B: `14:45:23.801 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `14:45:24.222 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `14:45:24.223 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `14:45:26.204 [INFO ] applying PCF segmentation`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.cobalt.log

lines v1=7, v1.1=7; only-in-v1 7, only-in-v1.1 7

- A: `11:01:30.897 [INFO ] Cobalt version 3.0`
- A: `11:01:30.902 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `11:01:31.023 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- A: `11:01:36.467 [INFO ] tumor depths(3088257) collected`
- A: `11:01:37.418 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `14:45:27.250 [INFO ] Cobalt version 3.0`
- B: `14:45:27.255 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `14:45:27.378 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- B: `14:45:33.058 [INFO ] tumor depths(3088257) collected`
- B: `14:45:34.192 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.purple.log

lines v1=20, v1.1=19; only-in-v1 20, only-in-v1.1 19

- A: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- A: `11:05:28.053 [INFO ] Purple version 4.4`
- A: `11:05:28.056 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- A: `11:05:28.057 [INFO ] output directory: purple/`
- A: `11:05:28.146 [INFO ] using ref genome: V38`
- B: `14:50:19.067 [INFO ] Purple version 4.4`
- B: `14:50:19.071 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- B: `14:50:19.071 [INFO ] output directory: purple/`
- B: `14:50:19.162 [INFO ] using ref genome: V38`
- B: `14:50:21.299 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

## Cosmetic-only differences (24)

- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_genebe_cache.json (only-in-v1 6, only-in-v1.1 6; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_mobidetails_cache.json (only-in-v1 6, only-in-v1.1 6; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_oncokb_cache.json (only-in-v1 6, only-in-v1.1 6; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_genebe_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_mobidetails_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_oncokb_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_genebe_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_mobidetails_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_oncokb_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:45 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_genebe_cache.json (only-in-v1 10, only-in-v1.1 10; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_mobidetails_cache.json (only-in-v1 10, only-in-v1.1 10; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_oncokb_cache.json (only-in-v1 10, only-in-v1.1 10; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_genebe_cache.json (only-in-v1 17, only-in-v1.1 17; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_mobidetails_cache.json (only-in-v1 17, only-in-v1.1 17; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_oncokb_cache.json (only-in-v1 17, only-in-v1.1 17; e.g. `    "_fetched_at": "2026-09-10 12:46 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_genebe_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_mobidetails_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_oncokb_cache.json (only-in-v1 5, only-in-v1.1 5; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_genebe_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_mobidetails_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_oncokb_cache.json (only-in-v1 7, only-in-v1.1 7; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_genebe_cache.json (only-in-v1 9, only-in-v1.1 9; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_mobidetails_cache.json (only-in-v1 9, only-in-v1.1 9; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_oncokb_cache.json (only-in-v1 9, only-in-v1.1 9; e.g. `    "_fetched_at": "2026-09-10 12:47 UTC",`)

## Binary / other files that differ by md5 (89)

- 26CGH1043-TwistMyVal/26CGH1043-TwistMyVal_report.zip
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

- only v1: tspipe_run8_img_reports.zip
- only v1.1: tspipe_run8_img11_reports.zip

