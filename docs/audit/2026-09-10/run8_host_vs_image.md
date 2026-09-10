# Run comparison: host (/goast/hemat_data/twist_val/tspipe_run8) vs image (/goast/hemat_data/twist_val/tspipe_run8_img) -- 2026-09-10

Files: 1394 common, 1275 only in host, 1 only in image. Common: 1079 identical (md5), 315 differ (102 real text differences, 24 cosmetic-only text differences, 189 binary/other).

Cosmetic = the differing lines match after masking paths, dates, run names, session ids and task hashes.

| Top-level dir | identical | real diff | cosmetic diff | binary diff |
|---|---|---|---|---|
| 26CGH1043-TwistMyVal | 153 | 7 | 3 | 13 |
| 26CGH1250-TwistMyVal | 161 | 7 | 3 | 13 |
| 26CGH1292-TwistMyVal | 78 | 31 | 3 | 56 |
| 26CGH132-TwistMyVal | 142 | 7 | 3 | 14 |
| 26CGH1480-TwistMyVal | 151 | 7 | 3 | 13 |
| 26CGH60-TwistMyVal | 144 | 7 | 3 | 14 |
| 26CGH799-TwistMyVal | 88 | 29 | 3 | 52 |
| 26CGH885-TwistMyVal | 149 | 7 | 3 | 13 |
| assets | 13 | 0 | 0 | 0 |
| cohort_index.html | 0 | 0 | 0 | 1 |

## Real text differences (102)

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:35:47 GMT 2026`
- B: `# Started on: Thu Sep 10 11:27:18 GMT 2026`

### 26CGH1043-TwistMyVal/clinical/cnv/reconcnv/26CGH1043-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1043-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1043-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.amber.log

lines host=6, image=6; only-in-host 6, only-in-image 6

- A: `07:18:04.300 [INFO ] Amber version 4.3`
- A: `07:18:06.814 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:18:07.241 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:18:07.241 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:18:09.155 [INFO ] applying PCF segmentation`
- B: `11:35:17.508 [INFO ] Amber version 4.3`
- B: `11:35:21.002 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:35:21.644 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:35:21.644 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `11:35:23.881 [INFO ] applying PCF segmentation`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:04.171 [INFO ] Cobalt version 3.0`
- A: `07:18:04.175 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:04.284 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- A: `07:18:09.859 [INFO ] tumor depths(3088257) collected`
- A: `07:18:11.400 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `11:32:28.366 [INFO ] Cobalt version 3.0`
- B: `11:32:28.371 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:32:28.516 [INFO ] calculating read depths from 26CGH1043-TwistMyVal.final.bam`
- B: `11:32:34.647 [INFO ] tumor depths(3088257) collected`
- B: `11:32:35.844 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1043-TwistMyVal/cnv_hmftools/26CGH1043-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:20.943 [INFO ] Purple version 4.4`
- A: `08:24:20.946 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- A: `08:24:20.946 [INFO ] output directory: purple/`
- A: `08:24:21.009 [INFO ] using ref genome: V38`
- A: `08:24:22.218 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `11:39:36.052 [INFO ] Purple version 4.4`
- B: `11:39:36.056 [INFO ] reference(NONE) tumor(26CGH1043-TwistMyVal) running on target-regions only`
- B: `11:39:36.056 [INFO ] output directory: purple/`
- B: `11:39:36.147 [INFO ] using ref genome: V38`
- B: `11:39:38.241 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1043-TwistMyVal/qc/26CGH1043-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH1043-TwistMyVal.final.bam (2810440123 bytes)`
- B: `OK 26CGH1043-TwistMyVal.final.bam (2810440112 bytes)`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:52:08 GMT 2026`
- B: `# Started on: Thu Sep 10 11:39:46 GMT 2026`

### 26CGH1250-TwistMyVal/clinical/cnv/reconcnv/26CGH1250-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1250-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1250-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.amber.log

lines host=6, image=7; only-in-host 6, only-in-image 7

- A: `15:51:26.107 [INFO ] Amber version 4.3`
- A: `15:51:29.322 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `15:51:29.890 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `15:51:29.891 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `15:51:32.071 [INFO ] applying PCF segmentation`
- B: `[0.016s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:56:33.741 [INFO ] Amber version 4.3`
- B: `11:56:37.251 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:56:37.708 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:56:37.709 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.cobalt.log

lines host=7, image=8; only-in-host 7, only-in-image 8

- A: `15:51:33.612 [INFO ] Cobalt version 3.0`
- A: `15:51:33.617 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `15:51:33.755 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- A: `15:51:40.393 [INFO ] tumor depths(3088257) collected`
- A: `15:51:41.884 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:54:39.021 [INFO ] Cobalt version 3.0`
- B: `11:54:39.026 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:54:39.173 [INFO ] calculating read depths from 26CGH1250-TwistMyVal.final.bam`
- B: `11:54:45.716 [INFO ] tumor depths(3088257) collected`

### 26CGH1250-TwistMyVal/cnv_hmftools/26CGH1250-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `15:54:44.910 [INFO ] Purple version 4.4`
- A: `15:54:44.913 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- A: `15:54:44.914 [INFO ] output directory: purple/`
- A: `15:54:44.992 [INFO ] using ref genome: V38`
- A: `15:54:47.257 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `12:02:12.180 [INFO ] Purple version 4.4`
- B: `12:02:12.194 [INFO ] reference(NONE) tumor(26CGH1250-TwistMyVal) running on target-regions only`
- B: `12:02:12.195 [INFO ] output directory: purple/`
- B: `12:02:12.403 [INFO ] using ref genome: V38`
- B: `12:02:14.135 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1250-TwistMyVal/qc/26CGH1250-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH1250-TwistMyVal.final.bam (3066024478 bytes)`
- B: `OK 26CGH1250-TwistMyVal.final.bam (3066024467 bytes)`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:53:08 GMT 2026`
- B: `# Started on: Thu Sep 10 11:37:28 GMT 2026`

### 26CGH1292-TwistMyVal/clinical/cnv/consensus/26CGH1292-TwistMyVal.cnv_consensus4.genes.tsv

lines host=136, image=136; only-in-host 69, only-in-image 69

- A: `GNB1	chr1	1785284	1891086	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUTR`
- A: `ARID1A	chr1	26696025	26782103	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	23	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:N`
- A: `CSF3R	chr1	36466041	36482922	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	17	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NE`
- A: `MPL	chr1	43337811	43354465	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUT`
- A: `GFI1	chr1	92473041	92486924	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	10	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEU`
- B: `GNB1	chr1	1785284	1891086	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUTR`
- B: `ARID1A	chr1	26696025	26782103	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	23	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:N`
- B: `CSF3R	chr1	36466041	36482922	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	17	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NE`
- B: `MPL	chr1	43337811	43354465	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUT`
- B: `GFI1	chr1	92473041	92486924	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	10	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEU`

### 26CGH1292-TwistMyVal/clinical/cnv/consensus/26CGH1292-TwistMyVal.cnv_consensus4.json

lines host=1, image=1; only-in-host 1, only-in-image 1

- A: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH1292-TwistMyVal", "status": "OK", "purity": "0.15", "ploidy": "2.01412046151552", "sex_inferred`
- B: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH1292-TwistMyVal", "status": "OK", "purity": "0.15", "ploidy": "2.01412046151552", "sex_inferred`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.chromosome_arm.tsv

lines host=42, image=42; only-in-host 41, only-in-image 41

- A: `1	P	2.3593	2.0665	1.8526	31.6450`
- A: `1	Q	1.9040	1.9040	1.9040	1.9040`
- A: `2	P	2.3621	2.1240	2.1240	29.6324`
- A: `2	Q	1.8704	1.8704	1.8704	1.8704`
- A: `3	P	2.1408	1.8704	1.7073	24.7182`
- B: `1	P	2.3641	2.0711	1.8572	31.6600`
- B: `1	Q	1.9086	1.9086	1.9086	1.9086`
- B: `2	P	2.3669	2.1287	2.1287	29.6467`
- B: `2	Q	1.8750	1.8750	1.8750	1.8750`
- B: `3	P	2.1455	1.8750	1.7118	24.7308`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.cnv.gene.tsv

lines host=39074, image=39074; only-in-host 39073, only-in-image 39073

- A: `chr1	12010	13670	DDX11L1	2.0665	2.0665	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	14696	24886	WASH7P	2.0665	2.0665	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	17369	17436	MIR6859-1	2.0665	2.0665	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	29554	31109	MIR1302-2HG	2.0665	2.0665	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	30366	30503	MIR1302-2	2.0665	2.0665	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- B: `chr1	12010	13670	DDX11L1	2.0711	2.0711	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	14696	24886	WASH7P	2.0711	2.0711	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	17369	17436	MIR6859-1	2.0711	2.0711	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	29554	31109	MIR1302-2HG	2.0711	2.0711	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	30366	30503	MIR1302-2	2.0711	2.0711	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.cnv.somatic.tsv

lines host=120, image=118; only-in-host 119, only-in-image 117

- A: `chr1	1	107865000	2.0665	93	0.5351	0.7276	TELOMERE	NONE	BAF_WEIGHTED	190	0.4678	1	1	0.5629	1.5036`
- A: `chr1	107865001	109193000	31.6450	2	0.6345	0.6827	NONE	NONE	BAF_WEIGHTED	1	0.2820	107394001	108336001	10.0398	21.6052`
- A: `chr1	109193001	123605522	1.8526	10	0.5365	0.7598	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4194	108337001	110049001	0.4450	1.4076`
- A: `chr1	123605523	248956422	1.9040	107	0.5400	0.7781	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4183	123605523	123605523	0.4225	1.4815`
- A: `chr2	1	18304500	2.2227	18	0.5326	0.5501	TELOMERE	NONE	BAF_WEIGHTED	27	0.4535	1	1	1.0000	1.2227`
- B: `chr1	1	107865000	2.0711	93	0.5351	0.7272	TELOMERE	NONE	BAF_WEIGHTED	190	0.4678	1	1	0.5651	1.5061`
- B: `chr1	107865001	109193000	31.6600	2	0.6345	0.6827	NONE	NONE	BAF_WEIGHTED	1	0.2820	107394001	108336001	10.0452	21.6147`
- B: `chr1	109193001	123605522	1.8572	10	0.5365	0.7592	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4194	108337001	110049001	0.4471	1.4100`
- B: `chr1	123605523	248956422	1.9086	107	0.5400	0.7775	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4183	123605523	123605523	0.4246	1.4840`
- B: `chr2	1	18304500	2.2275	18	0.5326	0.5511	TELOMERE	NONE	BAF_WEIGHTED	27	0.4535	1	1	1.0000	1.2275`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.driver.catalog.somatic.tsv

lines host=45, image=45; only-in-host 44, only-in-image 44

- A: `chr1	p13.2	NRAS	ENST00000369535	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.8526	1.8526`
- A: `chr1	q22	RIT1	ENST00000368323	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q31.1	BRINP3	ENST00000367462	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q32.1	UBE2T	ENST00000646651	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q42.2	EGLN1	ENST00000366641	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- B: `chr1	p13.2	NRAS	ENST00000369535	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.8572	1.8572`
- B: `chr1	q22	RIT1	ENST00000368323	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q31.1	BRINP3	ENST00000367462	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q32.1	UBE2T	ENST00000646651	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q42.2	EGLN1	ENST00000366641	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.h_genes.tsv

lines host=39074, image=39074; only-in-host 25039, only-in-image 25039

- A: `DDX11L1	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `WASH7P	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR6859-1	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR1302-2HG	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR1302-2	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- B: `DDX11L1	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `WASH7P	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR6859-1	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR1302-2HG	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR1302-2	NEUTRAL	2.07	2.07	0.57	FALSE	2`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.h_summary.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `26CGH1292-TwistMyVal	WARN_LOW_PURITY	NORMAL	0.150	2.000	FEMALE	TRUE	gain=1311;loss=2623;complex=4;loh=11992`
- B: `26CGH1292-TwistMyVal	WARN_LOW_PURITY	NORMAL	0.150	2.000	FEMALE	TRUE	gain=1311;loss=3076;complex=4;loh=12445`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.purity.range.tsv

lines host=15904, image=15904; only-in-host 15903, only-in-image 15903

- A: `1.0000	0.9629	0.2651	0.9755	2.0200	0.0000`
- A: `0.9900	0.9630	0.2654	0.9708	2.0200	0.0000`
- A: `0.9800	0.9631	0.2656	0.9708	2.0200	0.0000`
- A: `0.9700	0.9632	0.2657	0.9708	2.0200	0.0000`
- A: `1.0000	0.9726	0.2658	0.9832	2.0000	0.0000`
- B: `1.0000	0.9626	0.2667	0.9758	2.0200	0.0000`
- B: `0.9900	0.9627	0.2668	0.9711	2.0200	0.0000`
- B: `0.9800	0.9628	0.2669	0.9711	2.0200	0.0000`
- B: `0.9700	0.9629	0.2671	0.9711	2.0200	0.0000`
- B: `0.9600	0.9630	0.2674	0.9711	2.0200	0.0000`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.purity.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `0.1500	0.9726	0.4391	0.3645	2.0000	FEMALE	NORMAL	0.2910	0.3200	1.0000	1.9800	2.1000	0.5210	0.9832	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR	t`
- B: `0.1500	0.9722	0.4421	0.3645	2.0000	FEMALE	NORMAL	0.3068	0.3200	1.0000	1.9800	2.1000	0.5284	0.9835	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR	t`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.segment.tsv

lines host=205, image=203; only-in-host 123, only-in-image 121

- A: `chr1	1785001	107394000	DIPLOID	false	93	0.5351	0.4880	0.9774	1.0000	1.0000	0.5435	0.5911	2.0665	0.0000	0.0000	2.0665	true	NONE	190	0.7276	0.4678	1.3763	1	178500`
- A: `chr1	107394001	108337000	DIPLOID	false	2	0.6345	0.1000	3.1349	1.0000	1.0000	0.4463	0.0113	31.6450	0.0000	0.0000	31.6450	true	NONE	1	0.6827	0.2820	12.4580	107394`
- A: `chr1	108337001	119700000	DIPLOID	false	10	0.5365	0.4956	0.9618	1.0000	1.0000	0.4590	0.5756	1.8526	0.0000	0.0000	1.8526	true	NONE	21	0.7598	0.4194	1.3850	1083370`
- A: `chr1	123605523	248361000	DIPLOID	false	107	0.5400	0.4738	0.9656	1.0000	1.0000	0.5299	0.6021	1.9040	0.0000	0.0000	1.9040	true	CENTROMERE	148	0.7781	0.4183	1.4236`
- A: `chr2	615001	17866000	DIPLOID	false	18	0.5326	0.1000	0.9888	1.0000	1.0000	0.2617	0.1993	2.2227	0.0000	0.0000	2.2227	true	NONE	27	0.5501	0.4535	1.0891	1	615001`
- B: `chr1	1785001	107394000	DIPLOID	false	93	0.5351	0.4859	0.9774	1.0000	1.0000	0.5412	0.5886	2.0711	0.0000	0.0000	2.0711	true	NONE	190	0.7272	0.4678	1.3764	1	178500`
- B: `chr1	107394001	108337000	DIPLOID	false	2	0.6345	0.1000	3.1349	1.0000	1.0000	0.4367	0.0111	31.6600	0.0000	0.0000	31.6600	true	NONE	1	0.6827	0.2820	12.4640	107394`
- B: `chr1	108337001	119700000	DIPLOID	false	10	0.5365	0.4976	0.9618	1.0000	1.0000	0.4615	0.5783	1.8572	0.0000	0.0000	1.8572	true	NONE	21	0.7592	0.4194	1.3852	1083370`
- B: `chr1	123605523	248361000	DIPLOID	false	107	0.5400	0.4758	0.9656	1.0000	1.0000	0.5321	0.6047	1.9086	0.0000	0.0000	1.9086	true	CENTROMERE	148	0.7775	0.4183	1.4237`
- B: `chr2	615001	17866000	DIPLOID	false	18	0.5326	0.1000	0.9888	1.0000	1.0000	0.2671	0.2022	2.2275	0.0000	0.0000	2.2275	true	NONE	27	0.5511	0.4535	1.0910	1	615001`

### 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.target_region_cn.tsv

lines host=5317, image=5317; only-in-host 5316, only-in-image 5316

- A: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	19.7120	0.4170	-1.0000	1	107865000	2.0665	0.5629	190	93	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	27.2220	0.4737	-1.0000	1	107865000	2.0665	0.5629	190	93	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1294.0570	0.4725	1.0372	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHT`
- A: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2158.7840	0.3947	1.0178	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHTED`
- A: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	529.2680	0.5061	0.9091	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHTE`
- B: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	19.7120	0.4170	-1.0000	1	107865000	2.0711	0.5651	190	93	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	27.2220	0.4737	-1.0000	1	107865000	2.0711	0.5651	190	93	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1294.0570	0.4725	1.0372	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHT`
- B: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2158.7840	0.3947	1.0178	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHTED`
- B: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	529.2680	0.5061	0.9091	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHTE`

### 26CGH1292-TwistMyVal/clinical/cnv/reconcnv/26CGH1292-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1292-TwistMyVal/cnv_consensus_multi/26CGH1292-TwistMyVal.cnv_consensus4.genes.tsv

lines host=136, image=136; only-in-host 69, only-in-image 69

- A: `GNB1	chr1	1785284	1891086	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUTR`
- A: `ARID1A	chr1	26696025	26782103	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	23	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:N`
- A: `CSF3R	chr1	36466041	36482922	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	17	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NE`
- A: `MPL	chr1	43337811	43354465	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUT`
- A: `GFI1	chr1	92473041	92486924	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	10	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.56	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEU`
- B: `GNB1	chr1	1785284	1891086	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUTR`
- B: `ARID1A	chr1	26696025	26782103	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	23	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:N`
- B: `CSF3R	chr1	36466041	36482922	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	17	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NE`
- B: `MPL	chr1	43337811	43354465	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEUT`
- B: `GFI1	chr1	92473041	92486924	NEUTRAL	2	0.0159085	NEUTRAL	0.0027	10	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	2.07	2.07	0.57	FALSE	0	-	NEUTRAL	NA	0.000000	1p:NEU`

### 26CGH1292-TwistMyVal/cnv_consensus_multi/26CGH1292-TwistMyVal.cnv_consensus4.json

lines host=1, image=1; only-in-host 1, only-in-image 1

- A: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH1292-TwistMyVal", "status": "OK", "purity": "0.15", "ploidy": "2.01412046151552", "sex_inferred`
- B: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH1292-TwistMyVal", "status": "OK", "purity": "0.15", "ploidy": "2.01412046151552", "sex_inferred`

### 26CGH1292-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1292-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.amber.log

lines host=6, image=6; only-in-host 6, only-in-image 6

- A: `07:10:05.845 [INFO ] Amber version 4.3`
- A: `07:10:08.601 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:10:09.130 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:10:09.131 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:10:10.950 [INFO ] applying PCF segmentation`
- B: `11:44:55.143 [INFO ] Amber version 4.3`
- B: `11:44:58.919 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:44:59.561 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:44:59.562 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `11:45:01.936 [INFO ] applying PCF segmentation`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:09.967 [INFO ] Cobalt version 3.0`
- A: `07:18:09.971 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:10.082 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- A: `07:18:15.429 [INFO ] tumor depths(3088257) collected`
- A: `07:18:16.428 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `11:45:03.375 [INFO ] Cobalt version 3.0`
- B: `11:45:03.381 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:45:03.543 [INFO ] calculating read depths from 26CGH1292-TwistMyVal.final.bam`
- B: `11:45:09.046 [INFO ] tumor depths(3088257) collected`
- B: `11:45:10.080 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.purple.h_genes.tsv

lines host=39074, image=39074; only-in-host 25039, only-in-image 25039

- A: `DDX11L1	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `WASH7P	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR6859-1	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR1302-2HG	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- A: `MIR1302-2	NEUTRAL	2.07	2.07	0.56	FALSE	2`
- B: `DDX11L1	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `WASH7P	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR6859-1	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR1302-2HG	NEUTRAL	2.07	2.07	0.57	FALSE	2`
- B: `MIR1302-2	NEUTRAL	2.07	2.07	0.57	FALSE	2`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.purple.h_summary.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `26CGH1292-TwistMyVal	WARN_LOW_PURITY	NORMAL	0.150	2.000	FEMALE	TRUE	gain=1311;loss=2623;complex=4;loh=11992`
- B: `26CGH1292-TwistMyVal	WARN_LOW_PURITY	NORMAL	0.150	2.000	FEMALE	TRUE	gain=1311;loss=3076;complex=4;loh=12445`

### 26CGH1292-TwistMyVal/cnv_hmftools/26CGH1292-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:15.622 [INFO ] Purple version 4.4`
- A: `08:24:15.626 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- A: `08:24:15.626 [INFO ] output directory: purple/`
- A: `08:24:15.690 [INFO ] using ref genome: V38`
- A: `08:24:16.860 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `11:57:25.052 [INFO ] Purple version 4.4`
- B: `11:57:25.056 [INFO ] reference(NONE) tumor(26CGH1292-TwistMyVal) running on target-regions only`
- B: `11:57:25.056 [INFO ] output directory: purple/`
- B: `11:57:25.143 [INFO ] using ref genome: V38`
- B: `11:57:27.518 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.chromosome_arm.tsv

lines host=42, image=42; only-in-host 41, only-in-image 41

- A: `1	P	2.3593	2.0665	1.8526	31.6450`
- A: `1	Q	1.9040	1.9040	1.9040	1.9040`
- A: `2	P	2.3621	2.1240	2.1240	29.6324`
- A: `2	Q	1.8704	1.8704	1.8704	1.8704`
- A: `3	P	2.1408	1.8704	1.7073	24.7182`
- B: `1	P	2.3641	2.0711	1.8572	31.6600`
- B: `1	Q	1.9086	1.9086	1.9086	1.9086`
- B: `2	P	2.3669	2.1287	2.1287	29.6467`
- B: `2	Q	1.8750	1.8750	1.8750	1.8750`
- B: `3	P	2.1455	1.8750	1.7118	24.7308`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.cnv.gene.tsv

lines host=39074, image=39074; only-in-host 39073, only-in-image 39073

- A: `chr1	12010	13670	DDX11L1	2.0665	2.0665	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	14696	24886	WASH7P	2.0665	2.0665	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	17369	17436	MIR6859-1	2.0665	2.0665	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	29554	31109	MIR1302-2HG	2.0665	2.0665	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- A: `chr1	30366	30503	MIR1302-2	2.0665	2.0665	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5629	1.0332	190	0.4678	NONE	UNKNOWN`
- B: `chr1	12010	13670	DDX11L1	2.0711	2.0711	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	14696	24886	WASH7P	2.0711	2.0711	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	17369	17436	MIR6859-1	2.0711	2.0711	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	29554	31109	MIR1302-2HG	2.0711	2.0711	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`
- B: `chr1	30366	30503	MIR1302-2	2.0711	2.0711	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.5651	1.0356	190	0.4678	NONE	UNKNOWN`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.cnv.somatic.tsv

lines host=120, image=118; only-in-host 119, only-in-image 117

- A: `chr1	1	107865000	2.0665	93	0.5351	0.7276	TELOMERE	NONE	BAF_WEIGHTED	190	0.4678	1	1	0.5629	1.5036`
- A: `chr1	107865001	109193000	31.6450	2	0.6345	0.6827	NONE	NONE	BAF_WEIGHTED	1	0.2820	107394001	108336001	10.0398	21.6052`
- A: `chr1	109193001	123605522	1.8526	10	0.5365	0.7598	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4194	108337001	110049001	0.4450	1.4076`
- A: `chr1	123605523	248956422	1.9040	107	0.5400	0.7781	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4183	123605523	123605523	0.4225	1.4815`
- A: `chr2	1	18304500	2.2227	18	0.5326	0.5501	TELOMERE	NONE	BAF_WEIGHTED	27	0.4535	1	1	1.0000	1.2227`
- B: `chr1	1	107865000	2.0711	93	0.5351	0.7272	TELOMERE	NONE	BAF_WEIGHTED	190	0.4678	1	1	0.5651	1.5061`
- B: `chr1	107865001	109193000	31.6600	2	0.6345	0.6827	NONE	NONE	BAF_WEIGHTED	1	0.2820	107394001	108336001	10.0452	21.6147`
- B: `chr1	109193001	123605522	1.8572	10	0.5365	0.7592	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4194	108337001	110049001	0.4471	1.4100`
- B: `chr1	123605523	248956422	1.9086	107	0.5400	0.7775	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4183	123605523	123605523	0.4246	1.4840`
- B: `chr2	1	18304500	2.2275	18	0.5326	0.5511	TELOMERE	NONE	BAF_WEIGHTED	27	0.4535	1	1	1.0000	1.2275`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.driver.catalog.somatic.tsv

lines host=45, image=45; only-in-host 44, only-in-image 44

- A: `chr1	p13.2	NRAS	ENST00000369535	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.8526	1.8526`
- A: `chr1	q22	RIT1	ENST00000368323	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q31.1	BRINP3	ENST00000367462	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q32.1	UBE2T	ENST00000646651	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- A: `chr1	q42.2	EGLN1	ENST00000366641	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9040	1.9040`
- B: `chr1	p13.2	NRAS	ENST00000369535	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.8572	1.8572`
- B: `chr1	q22	RIT1	ENST00000368323	true	LOH	ONCO	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q31.1	BRINP3	ENST00000367462	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q32.1	UBE2T	ENST00000646651	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`
- B: `chr1	q42.2	EGLN1	ENST00000366641	true	LOH	TSG	DEL	NOT_REPORTED	0.0000	0	0	0	0	0	false	1.9086	1.9086`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.purity.range.tsv

lines host=15904, image=15904; only-in-host 15903, only-in-image 15903

- A: `1.0000	0.9629	0.2651	0.9755	2.0200	0.0000`
- A: `0.9900	0.9630	0.2654	0.9708	2.0200	0.0000`
- A: `0.9800	0.9631	0.2656	0.9708	2.0200	0.0000`
- A: `0.9700	0.9632	0.2657	0.9708	2.0200	0.0000`
- A: `1.0000	0.9726	0.2658	0.9832	2.0000	0.0000`
- B: `1.0000	0.9626	0.2667	0.9758	2.0200	0.0000`
- B: `0.9900	0.9627	0.2668	0.9711	2.0200	0.0000`
- B: `0.9800	0.9628	0.2669	0.9711	2.0200	0.0000`
- B: `0.9700	0.9629	0.2671	0.9711	2.0200	0.0000`
- B: `0.9600	0.9630	0.2674	0.9711	2.0200	0.0000`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.purity.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `0.1500	0.9726	0.4391	0.3645	2.0000	FEMALE	NORMAL	0.2910	0.3200	1.0000	1.9800	2.1000	0.5210	0.9832	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR	t`
- B: `0.1500	0.9722	0.4421	0.3645	2.0000	FEMALE	NORMAL	0.3068	0.3200	1.0000	1.9800	2.1000	0.5284	0.9835	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR	t`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.segment.tsv

lines host=205, image=203; only-in-host 123, only-in-image 121

- A: `chr1	1785001	107394000	DIPLOID	false	93	0.5351	0.4880	0.9774	1.0000	1.0000	0.5435	0.5911	2.0665	0.0000	0.0000	2.0665	true	NONE	190	0.7276	0.4678	1.3763	1	178500`
- A: `chr1	107394001	108337000	DIPLOID	false	2	0.6345	0.1000	3.1349	1.0000	1.0000	0.4463	0.0113	31.6450	0.0000	0.0000	31.6450	true	NONE	1	0.6827	0.2820	12.4580	107394`
- A: `chr1	108337001	119700000	DIPLOID	false	10	0.5365	0.4956	0.9618	1.0000	1.0000	0.4590	0.5756	1.8526	0.0000	0.0000	1.8526	true	NONE	21	0.7598	0.4194	1.3850	1083370`
- A: `chr1	123605523	248361000	DIPLOID	false	107	0.5400	0.4738	0.9656	1.0000	1.0000	0.5299	0.6021	1.9040	0.0000	0.0000	1.9040	true	CENTROMERE	148	0.7781	0.4183	1.4236`
- A: `chr2	615001	17866000	DIPLOID	false	18	0.5326	0.1000	0.9888	1.0000	1.0000	0.2617	0.1993	2.2227	0.0000	0.0000	2.2227	true	NONE	27	0.5501	0.4535	1.0891	1	615001`
- B: `chr1	1785001	107394000	DIPLOID	false	93	0.5351	0.4859	0.9774	1.0000	1.0000	0.5412	0.5886	2.0711	0.0000	0.0000	2.0711	true	NONE	190	0.7272	0.4678	1.3764	1	178500`
- B: `chr1	107394001	108337000	DIPLOID	false	2	0.6345	0.1000	3.1349	1.0000	1.0000	0.4367	0.0111	31.6600	0.0000	0.0000	31.6600	true	NONE	1	0.6827	0.2820	12.4640	107394`
- B: `chr1	108337001	119700000	DIPLOID	false	10	0.5365	0.4976	0.9618	1.0000	1.0000	0.4615	0.5783	1.8572	0.0000	0.0000	1.8572	true	NONE	21	0.7592	0.4194	1.3852	1083370`
- B: `chr1	123605523	248361000	DIPLOID	false	107	0.5400	0.4758	0.9656	1.0000	1.0000	0.5321	0.6047	1.9086	0.0000	0.0000	1.9086	true	CENTROMERE	148	0.7775	0.4183	1.4237`
- B: `chr2	615001	17866000	DIPLOID	false	18	0.5326	0.1000	0.9888	1.0000	1.0000	0.2671	0.2022	2.2275	0.0000	0.0000	2.2275	true	NONE	27	0.5511	0.4535	1.0910	1	615001`

### 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.target_region_cn.tsv

lines host=5317, image=5317; only-in-host 5316, only-in-image 5316

- A: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	19.7120	0.4170	-1.0000	1	107865000	2.0665	0.5629	190	93	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	27.2220	0.4737	-1.0000	1	107865000	2.0665	0.5629	190	93	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1294.0570	0.4725	1.0372	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHT`
- A: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2158.7840	0.3947	1.0178	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHTED`
- A: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	529.2680	0.5061	0.9091	1	107865000	2.0665	0.5629	190	93	DIPLOID	BAF_WEIGHTE`
- B: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	19.7120	0.4170	-1.0000	1	107865000	2.0711	0.5651	190	93	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	27.2220	0.4737	-1.0000	1	107865000	2.0711	0.5651	190	93	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1294.0570	0.4725	1.0372	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHT`
- B: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2158.7840	0.3947	1.0178	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHTED`
- B: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	529.2680	0.5061	0.9091	1	107865000	2.0711	0.5651	190	93	DIPLOID	BAF_WEIGHTE`

### 26CGH1292-TwistMyVal/qc/26CGH1292-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH1292-TwistMyVal.final.bam (3103373444 bytes)`
- B: `OK 26CGH1292-TwistMyVal.final.bam (3103373433 bytes)`

### 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 16:12:09 GMT 2026`
- B: `# Started on: Thu Sep 10 12:02:34 GMT 2026`

### 26CGH132-TwistMyVal/clinical/cnv/reconcnv/26CGH132-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH132-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH132-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.amber.log

lines host=6, image=6; only-in-host 6, only-in-image 6

- A: `07:10:05.722 [INFO ] Amber version 4.3`
- A: `07:10:08.307 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:10:08.668 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:10:08.668 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:10:10.458 [INFO ] applying PCF segmentation`
- B: `12:17:18.448 [INFO ] Amber version 4.3`
- B: `12:17:21.699 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `12:17:22.404 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `12:17:22.404 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `12:17:24.553 [INFO ] applying PCF segmentation`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:18.222 [INFO ] Cobalt version 3.0`
- A: `07:18:18.227 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:18.343 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- A: `07:18:24.297 [INFO ] tumor depths(3088257) collected`
- A: `07:18:25.752 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `12:17:26.273 [INFO ] Cobalt version 3.0`
- B: `12:17:26.279 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `12:17:26.423 [INFO ] calculating read depths from 26CGH132-TwistMyVal.final.bam`
- B: `12:17:32.382 [INFO ] tumor depths(3088257) collected`
- B: `12:17:33.384 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH132-TwistMyVal/cnv_hmftools/26CGH132-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:20.871 [INFO ] Purple version 4.4`
- A: `08:24:20.875 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- A: `08:24:20.875 [INFO ] output directory: purple/`
- A: `08:24:20.938 [INFO ] using ref genome: V38`
- A: `08:24:22.191 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `12:23:12.731 [INFO ] Purple version 4.4`
- B: `12:23:12.734 [INFO ] reference(NONE) tumor(26CGH132-TwistMyVal) running on target-regions only`
- B: `12:23:12.734 [INFO ] output directory: purple/`
- B: `12:23:12.822 [INFO ] using ref genome: V38`
- B: `12:23:14.818 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH132-TwistMyVal/qc/26CGH132-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH132-TwistMyVal.final.bam (3835869783 bytes)`
- B: `OK 26CGH132-TwistMyVal.final.bam (3835869772 bytes)`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:32:53 GMT 2026`
- B: `# Started on: Thu Sep 10 11:17:01 GMT 2026`

### 26CGH1480-TwistMyVal/clinical/cnv/reconcnv/26CGH1480-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1480-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1480-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.amber.log

lines host=6, image=7; only-in-host 6, only-in-image 7

- A: `07:18:10.455 [INFO ] Amber version 4.3`
- A: `07:18:13.287 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:18:14.216 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:18:14.217 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:18:16.059 [INFO ] applying PCF segmentation`
- B: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:24:44.849 [INFO ] Amber version 4.3`
- B: `11:24:48.182 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:24:48.933 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:24:48.934 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.cobalt.log

lines host=7, image=8; only-in-host 7, only-in-image 8

- A: `07:18:16.893 [INFO ] Cobalt version 3.0`
- A: `07:18:16.897 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:17.009 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- A: `07:18:21.804 [INFO ] tumor depths(3088257) collected`
- A: `07:18:22.819 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `[0.016s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:25:08.368 [INFO ] Cobalt version 3.0`
- B: `11:25:08.373 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:25:08.494 [INFO ] calculating read depths from 26CGH1480-TwistMyVal.final.bam`
- B: `11:25:13.797 [INFO ] tumor depths(3088257) collected`

### 26CGH1480-TwistMyVal/cnv_hmftools/26CGH1480-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:15.697 [INFO ] Purple version 4.4`
- A: `08:24:15.701 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- A: `08:24:15.701 [INFO ] output directory: purple/`
- A: `08:24:15.764 [INFO ] using ref genome: V38`
- A: `08:24:16.951 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `11:28:50.931 [INFO ] Purple version 4.4`
- B: `11:28:50.934 [INFO ] reference(NONE) tumor(26CGH1480-TwistMyVal) running on target-regions only`
- B: `11:28:50.934 [INFO ] output directory: purple/`
- B: `11:28:51.007 [INFO ] using ref genome: V38`
- B: `11:28:53.151 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH1480-TwistMyVal/qc/26CGH1480-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH1480-TwistMyVal.final.bam (2687658709 bytes)`
- B: `OK 26CGH1480-TwistMyVal.final.bam (2687658698 bytes)`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 16:14:25 GMT 2026`
- B: `# Started on: Thu Sep 10 11:57:56 GMT 2026`

### 26CGH60-TwistMyVal/clinical/cnv/reconcnv/26CGH60-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH60-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH60-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.amber.log

lines host=6, image=6; only-in-host 6, only-in-image 6

- A: `07:18:20.228 [INFO ] Amber version 4.3`
- A: `07:18:23.514 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:18:24.029 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:18:24.029 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:18:25.937 [INFO ] applying PCF segmentation`
- B: `12:04:46.232 [INFO ] Amber version 4.3`
- B: `12:04:49.712 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `12:04:50.345 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `12:04:50.346 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `12:04:52.563 [INFO ] applying PCF segmentation`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:10.141 [INFO ] Cobalt version 3.0`
- A: `07:18:10.146 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:10.260 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- A: `07:18:16.438 [INFO ] tumor depths(3088257) collected`
- A: `07:18:17.420 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `12:08:23.364 [INFO ] Cobalt version 3.0`
- B: `12:08:23.369 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `12:08:23.514 [INFO ] calculating read depths from 26CGH60-TwistMyVal.final.bam`
- B: `12:08:29.766 [INFO ] tumor depths(3088257) collected`
- B: `12:08:30.764 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH60-TwistMyVal/cnv_hmftools/26CGH60-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:15.685 [INFO ] Purple version 4.4`
- A: `08:24:15.688 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- A: `08:24:15.688 [INFO ] output directory: purple/`
- A: `08:24:15.767 [INFO ] using ref genome: V38`
- A: `08:24:17.589 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `12:21:58.172 [INFO ] Purple version 4.4`
- B: `12:21:58.176 [INFO ] reference(NONE) tumor(26CGH60-TwistMyVal) running on target-regions only`
- B: `12:21:58.176 [INFO ] output directory: purple/`
- B: `12:21:58.264 [INFO ] using ref genome: V38`
- B: `12:22:00.326 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH60-TwistMyVal/qc/26CGH60-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH60-TwistMyVal.final.bam (3244138445 bytes)`
- B: `OK 26CGH60-TwistMyVal.final.bam (3244138432 bytes)`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:23:15 GMT 2026`
- B: `# Started on: Thu Sep 10 11:05:54 GMT 2026`

### 26CGH799-TwistMyVal/clinical/cnv/consensus/26CGH799-TwistMyVal.cnv_consensus4.genes.tsv

lines host=136, image=136; only-in-host 51, only-in-image 51

- A: `HRAS	chr11	532240	535591	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	5	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p:NEUT`
- A: `RRAS2	chr11	14277920	14359182	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	6	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p`
- A: `WT1	chr11	32387773	32435538	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	12	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p:`
- A: `BIRC3	chr11	102317451	102339402	NEUTRAL	2	0.00734366	NEUTRAL	-0.0074	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.87	1.87	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	`
- A: `ATM	chr11	108223065	108369101	NEUTRAL	2	-0.0145104	NEUTRAL	-0.0074	67	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.87	1.87	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11`
- B: `HRAS	chr11	532240	535591	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	5	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p:NEUT`
- B: `RRAS2	chr11	14277920	14359182	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	6	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p`
- B: `WT1	chr11	32387773	32435538	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	12	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p:`
- B: `BIRC3	chr11	102317451	102339402	NEUTRAL	2	0.00734366	NEUTRAL	-0.0074	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.86	1.86	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	`
- B: `ATM	chr11	108223065	108369101	NEUTRAL	2	-0.0145104	NEUTRAL	-0.0074	67	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.86	1.86	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11`

### 26CGH799-TwistMyVal/clinical/cnv/consensus/26CGH799-TwistMyVal.cnv_consensus4.json

lines host=1, image=1; only-in-host 1, only-in-image 1

- A: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH799-TwistMyVal", "status": "OK", "purity": "0.3", "ploidy": "2.02158423289877", "sex_inferred":`
- B: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH799-TwistMyVal", "status": "OK", "purity": "0.3", "ploidy": "2.02158423289877", "sex_inferred":`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.chromosome_arm.tsv

lines host=42, image=42; only-in-host 41, only-in-image 41

- A: `1	P	2.0021	1.9546	1.9440	6.4934`
- A: `1	Q	1.9783	1.9783	1.9783	1.9783`
- A: `2	P	2.0069	1.9868	1.9632	5.0953`
- A: `2	Q	2.0283	1.9783	1.8923	8.7649`
- A: `3	P	2.0427	1.9641	1.9580	5.4754`
- B: `1	P	1.9991	1.9517	1.9411	6.4838`
- B: `1	Q	1.9754	1.9754	1.9754	1.9754`
- B: `2	P	2.0039	1.9839	1.9603	5.0877`
- B: `2	Q	2.0253	1.9754	1.8895	8.7519`
- B: `3	P	2.0397	1.9612	1.9551	5.4673`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.cnv.gene.tsv

lines host=39074, image=39074; only-in-host 39073, only-in-image 39073

- A: `chr1	12010	13670	DDX11L1	1.9546	1.9546	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	14696	24886	WASH7P	1.9546	1.9546	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	17369	17436	MIR6859-1	1.9546	1.9546	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	29554	31109	MIR1302-2HG	1.9546	1.9546	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	30366	30503	MIR1302-2	1.9546	1.9546	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- B: `chr1	12010	13670	DDX11L1	1.9517	1.9517	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	14696	24886	WASH7P	1.9517	1.9517	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	17369	17436	MIR6859-1	1.9517	1.9517	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	29554	31109	MIR1302-2HG	1.9517	1.9517	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	30366	30503	MIR1302-2	1.9517	1.9517	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.cnv.somatic.tsv

lines host=116, image=120; only-in-host 115, only-in-image 119

- A: `chr1	1	107865000	1.9546	78	0.5376	0.5376	TELOMERE	NONE	BAF_WEIGHTED	190	0.4674	1	1	0.9038	1.0508`
- A: `chr1	107865001	109193000	6.4934	2	0.6946	0.6946	NONE	NONE	BAF_WEIGHTED	1	0.2812	107394001	108336001	1.9834	4.5100`
- A: `chr1	109193001	123605522	1.9440	7	0.5739	0.5739	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4191	108337001	110049001	0.8283	1.1157`
- A: `chr1	123605523	248956422	1.9783	93	0.5333	0.5055	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4177	123605523	123605523	0.9783	1.0000`
- A: `chr2	1	18304500	1.9632	20	0.5263	0.5094	TELOMERE	NONE	BAF_WEIGHTED	26	0.4452	1	1	0.9632	1.0000`
- B: `chr1	1	107865000	1.9517	78	0.5376	0.5376	TELOMERE	NONE	BAF_WEIGHTED	190	0.4674	1	1	0.9024	1.0492`
- B: `chr1	107865001	109193000	6.4838	2	0.6946	0.6946	NONE	NONE	BAF_WEIGHTED	1	0.2812	107394001	108336001	1.9805	4.5033`
- B: `chr1	109193001	123605522	1.9411	7	0.5739	0.5739	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4191	108337001	110049001	0.8271	1.1140`
- B: `chr1	123605523	248956422	1.9754	93	0.5333	0.5062	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4177	123605523	123605523	0.9754	1.0000`
- B: `chr2	1	18304500	1.9603	20	0.5263	0.5101	TELOMERE	NONE	BAF_WEIGHTED	26	0.4452	1	1	0.9603	1.0000`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.h_genes.tsv

lines host=39074, image=39074; only-in-host 13938, only-in-image 13938

- A: `VAV3	GAIN	1.95	6.49	0.90	FALSE	2`
- A: `MIR7852	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `VAV3-AS1	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `LINC02785	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `SLC25A24	GAIN	6.49	6.49	1.98	FALSE	2`
- B: `VAV3	GAIN	1.95	6.48	0.90	FALSE	2`
- B: `MIR7852	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `VAV3-AS1	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `LINC02785	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `SLC25A24	GAIN	6.48	6.48	1.98	FALSE	2`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.h_summary.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `26CGH799-TwistMyVal	FAIL_NO_TUMOR	NO_TUMOR	1.000	2.000	FEMALE	FALSE	gain=378;loss=37;complex=0;loh=37`
- B: `26CGH799-TwistMyVal	FAIL_NO_TUMOR	NO_TUMOR	1.000	2.000	FEMALE	FALSE	gain=381;loss=37;complex=0;loh=37`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.purity.range.tsv

lines host=15904, image=15904; only-in-host 15903, only-in-image 15903

- A: `1.0000	0.9563	0.2816	0.9416	2.0400	0.0000`
- A: `0.9900	0.9565	0.2818	0.9416	2.0400	0.0000`
- A: `0.9800	0.9567	0.2819	0.9416	2.0400	0.0000`
- A: `0.9700	0.9569	0.2821	0.9416	2.0400	0.0000`
- A: `0.9600	0.9570	0.2824	0.9416	2.0400	0.0000`
- B: `1.0000	0.9577	0.2812	0.9416	2.0400	0.0000`
- B: `0.9900	0.9579	0.2814	0.9416	2.0400	0.0000`
- B: `0.9800	0.9581	0.2817	0.9416	2.0400	0.0000`
- B: `0.9700	0.9583	0.2819	0.9416	2.0400	0.0000`
- B: `0.9600	0.9585	0.2822	0.9416	2.0400	0.0000`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.purity.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `1.0000	0.9754	0.2988	0.9416	2.0000	FEMALE	NO_TUMOR	0.0497	0.3100	1.0000	2.0000	2.2200	0.4170	0.9416	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR`
- B: `1.0000	0.9769	0.3010	0.9416	2.0000	FEMALE	NO_TUMOR	0.0497	0.3100	1.0000	2.0000	2.2200	0.4214	0.9416	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.segment.tsv

lines host=206, image=210; only-in-host 124, only-in-image 128

- A: `chr1	1785001	107394000	DIPLOID	false	78	0.5376	0.3611	0.9532	1.0000	1.0000	0.1956	0.3455	1.9546	0.0000	0.0000	1.9546	true	NONE	190	0.5376	0.4674	1.0588	1	178500`
- A: `chr1	107394001	108337000	DIPLOID	false	2	0.6946	0.1000	3.1669	1.0000	1.0000	0.9831	0.0237	6.4934	0.0000	0.0000	6.4934	true	NONE	1	0.6946	0.2812	2.4106	107394001`
- A: `chr1	108337001	119700000	DIPLOID	false	7	0.5739	0.5975	0.9481	1.0000	1.0000	0.4273	0.6901	1.9440	0.0000	0.0000	1.9440	true	NONE	21	0.5739	0.4191	1.1149	10833700`
- A: `chr1	123605523	248361000	DIPLOID	false	93	0.5333	0.1000	0.9648	1.0000	1.0000	0.1000	0.1187	1.9783	0.0000	0.0000	1.9783	true	CENTROMERE	148	0.5055	0.4177	1.0087	`
- A: `chr2	615001	17866000	DIPLOID	false	20	0.5263	0.1426	0.9574	1.0000	1.0000	0.1000	0.1455	1.9632	0.0000	0.0000	1.9632	true	NONE	26	0.5094	0.4452	1.0147	1	615001`
- B: `chr1	1785001	107394000	DIPLOID	false	78	0.5376	0.3663	0.9532	1.0000	1.0000	0.1899	0.3452	1.9517	0.0000	0.0000	1.9517	true	NONE	190	0.5376	0.4674	1.0587	1	178500`
- B: `chr1	107394001	108337000	DIPLOID	false	2	0.6946	0.1000	3.1669	1.0000	1.0000	0.9847	0.0237	6.4838	0.0000	0.0000	6.4838	true	NONE	1	0.6946	0.2812	2.4091	107394001`
- B: `chr1	108337001	119700000	DIPLOID	false	7	0.5739	0.6016	0.9481	1.0000	1.0000	0.4224	0.6895	1.9411	0.0000	0.0000	1.9411	true	NONE	21	0.5739	0.4191	1.1148	10833700`
- B: `chr1	123605523	248361000	DIPLOID	false	93	0.5333	0.1000	0.9648	1.0000	1.0000	0.1000	0.1187	1.9754	0.0000	0.0000	1.9754	true	CENTROMERE	148	0.5062	0.4177	1.0098	`
- B: `chr2	615001	17866000	DIPLOID	false	20	0.5263	0.1539	0.9574	1.0000	1.0000	0.1000	0.1523	1.9603	0.0000	0.0000	1.9603	true	NONE	26	0.5101	0.4452	1.0159	1	615001`

### 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.target_region_cn.tsv

lines host=5317, image=5317; only-in-host 5316, only-in-image 5316

- A: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	24.9800	0.4144	-1.0000	1	107865000	1.9546	0.9038	190	78	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	29.7660	0.4806	-1.0000	1	107865000	1.9546	0.9038	190	78	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1202.4520	0.4701	1.0507	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHT`
- A: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2071.8730	0.3942	1.0354	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHTED`
- A: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	493.0200	0.5037	0.9249	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHTE`
- B: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	24.9800	0.4144	-1.0000	1	107865000	1.9517	0.9024	190	78	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	29.7660	0.4806	-1.0000	1	107865000	1.9517	0.9024	190	78	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1202.4520	0.4701	1.0507	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHT`
- B: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2071.8730	0.3942	1.0354	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHTED`
- B: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	493.0200	0.5037	0.9249	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHTE`

### 26CGH799-TwistMyVal/clinical/cnv/reconcnv/26CGH799-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH799-TwistMyVal/cnv_consensus_multi/26CGH799-TwistMyVal.cnv_consensus4.genes.tsv

lines host=136, image=136; only-in-host 51, only-in-image 51

- A: `HRAS	chr11	532240	535591	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	5	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p:NEUT`
- A: `RRAS2	chr11	14277920	14359182	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	6	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p`
- A: `WT1	chr11	32387773	32435538	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	12	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.92	1.92	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11p:`
- A: `BIRC3	chr11	102317451	102339402	NEUTRAL	2	0.00734366	NEUTRAL	-0.0074	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.87	1.87	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	`
- A: `ATM	chr11	108223065	108369101	NEUTRAL	2	-0.0145104	NEUTRAL	-0.0074	67	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.87	1.87	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11`
- B: `HRAS	chr11	532240	535591	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	5	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p:NEUT`
- B: `RRAS2	chr11	14277920	14359182	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	6	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p`
- B: `WT1	chr11	32387773	32435538	NEUTRAL	2	-0.0121403	NEUTRAL	-0.0074	12	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.91	1.91	0.91	FALSE	0	-	NEUTRAL	NA	0.000000	11p:`
- B: `BIRC3	chr11	102317451	102339402	NEUTRAL	2	0.00734366	NEUTRAL	-0.0074	13	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.86	1.86	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	`
- B: `ATM	chr11	108223065	108369101	NEUTRAL	2	-0.0145104	NEUTRAL	-0.0074	67	NEUTRAL	NEUTRAL	2	false	NEUTRAL	NA	NEUTRAL	1.86	1.86	0.92	FALSE	0	-	NEUTRAL	NA	0.000000	11`

### 26CGH799-TwistMyVal/cnv_consensus_multi/26CGH799-TwistMyVal.cnv_consensus4.json

lines host=1, image=1; only-in-host 1, only-in-image 1

- A: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH799-TwistMyVal", "status": "OK", "purity": "0.3", "ploidy": "2.02158423289877", "sex_inferred":`
- B: `{"schema": "twist_cnv_consensus4/v4", "purecn": {"sample": "26CGH799-TwistMyVal", "status": "OK", "purity": "0.3", "ploidy": "2.02158423289877", "sex_inferred":`

### 26CGH799-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH799-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.amber.log

lines host=6, image=7; only-in-host 6, only-in-image 7

- A: `07:10:05.780 [INFO ] Amber version 4.3`
- A: `07:10:08.383 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:10:08.793 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:10:08.793 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:10:10.485 [INFO ] applying PCF segmentation`
- B: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:12:18.859 [INFO ] Amber version 4.3`
- B: `11:12:22.294 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:12:23.020 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:12:23.021 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:20.954 [INFO ] Cobalt version 3.0`
- A: `07:18:20.959 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:21.071 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- A: `07:18:26.804 [INFO ] tumor depths(3088257) collected`
- A: `07:18:27.902 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `11:10:16.704 [INFO ] Cobalt version 3.0`
- B: `11:10:16.710 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:10:16.862 [INFO ] calculating read depths from 26CGH799-TwistMyVal.final.bam`
- B: `11:10:22.877 [INFO ] tumor depths(3088257) collected`
- B: `11:10:24.186 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.purple.h_genes.tsv

lines host=39074, image=39074; only-in-host 13938, only-in-image 13938

- A: `VAV3	GAIN	1.95	6.49	0.90	FALSE	2`
- A: `MIR7852	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `VAV3-AS1	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `LINC02785	GAIN	6.49	6.49	1.98	FALSE	2`
- A: `SLC25A24	GAIN	6.49	6.49	1.98	FALSE	2`
- B: `VAV3	GAIN	1.95	6.48	0.90	FALSE	2`
- B: `MIR7852	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `VAV3-AS1	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `LINC02785	GAIN	6.48	6.48	1.98	FALSE	2`
- B: `SLC25A24	GAIN	6.48	6.48	1.98	FALSE	2`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.purple.h_summary.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `26CGH799-TwistMyVal	FAIL_NO_TUMOR	NO_TUMOR	1.000	2.000	FEMALE	FALSE	gain=378;loss=37;complex=0;loh=37`
- B: `26CGH799-TwistMyVal	FAIL_NO_TUMOR	NO_TUMOR	1.000	2.000	FEMALE	FALSE	gain=381;loss=37;complex=0;loh=37`

### 26CGH799-TwistMyVal/cnv_hmftools/26CGH799-TwistMyVal.purple.log

lines host=19, image=19; only-in-host 19, only-in-image 19

- A: `08:24:15.674 [INFO ] Purple version 4.4`
- A: `08:24:15.678 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- A: `08:24:15.678 [INFO ] output directory: purple/`
- A: `08:24:15.756 [INFO ] using ref genome: V38`
- A: `08:24:17.433 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `11:18:58.536 [INFO ] Purple version 4.4`
- B: `11:18:58.540 [INFO ] reference(NONE) tumor(26CGH799-TwistMyVal) running on target-regions only`
- B: `11:18:58.540 [INFO ] output directory: purple/`
- B: `11:18:58.629 [INFO ] using ref genome: V38`
- B: `11:19:00.891 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.chromosome_arm.tsv

lines host=42, image=42; only-in-host 41, only-in-image 41

- A: `1	P	2.0021	1.9546	1.9440	6.4934`
- A: `1	Q	1.9783	1.9783	1.9783	1.9783`
- A: `2	P	2.0069	1.9868	1.9632	5.0953`
- A: `2	Q	2.0283	1.9783	1.8923	8.7649`
- A: `3	P	2.0427	1.9641	1.9580	5.4754`
- B: `1	P	1.9991	1.9517	1.9411	6.4838`
- B: `1	Q	1.9754	1.9754	1.9754	1.9754`
- B: `2	P	2.0039	1.9839	1.9603	5.0877`
- B: `2	Q	2.0253	1.9754	1.8895	8.7519`
- B: `3	P	2.0397	1.9612	1.9551	5.4673`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.cnv.gene.tsv

lines host=39074, image=39074; only-in-host 39073, only-in-image 39073

- A: `chr1	12010	13670	DDX11L1	1.9546	1.9546	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	14696	24886	WASH7P	1.9546	1.9546	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	17369	17436	MIR6859-1	1.9546	1.9546	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	29554	31109	MIR1302-2HG	1.9546	1.9546	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- A: `chr1	30366	30503	MIR1302-2	1.9546	1.9546	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9038	0.9773	190	0.4674	NONE	UNKNOWN`
- B: `chr1	12010	13670	DDX11L1	1.9517	1.9517	1	ENST00000450305	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	14696	24886	WASH7P	1.9517	1.9517	1	ENST00000488147	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	17369	17436	MIR6859-1	1.9517	1.9517	1	ENST00000619216	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	29554	31109	MIR1302-2HG	1.9517	1.9517	1	ENST00000473358	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`
- B: `chr1	30366	30503	MIR1302-2	1.9517	1.9517	1	ENST00000607096	true	p36.33	1	1	107865000	TELOMERE	NONE	BAF_WEIGHTED	0.9024	0.9758	190	0.4674	NONE	UNKNOWN`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.cnv.somatic.tsv

lines host=116, image=120; only-in-host 115, only-in-image 119

- A: `chr1	1	107865000	1.9546	78	0.5376	0.5376	TELOMERE	NONE	BAF_WEIGHTED	190	0.4674	1	1	0.9038	1.0508`
- A: `chr1	107865001	109193000	6.4934	2	0.6946	0.6946	NONE	NONE	BAF_WEIGHTED	1	0.2812	107394001	108336001	1.9834	4.5100`
- A: `chr1	109193001	123605522	1.9440	7	0.5739	0.5739	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4191	108337001	110049001	0.8283	1.1157`
- A: `chr1	123605523	248956422	1.9783	93	0.5333	0.5055	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4177	123605523	123605523	0.9783	1.0000`
- A: `chr2	1	18304500	1.9632	20	0.5263	0.5094	TELOMERE	NONE	BAF_WEIGHTED	26	0.4452	1	1	0.9632	1.0000`
- B: `chr1	1	107865000	1.9517	78	0.5376	0.5376	TELOMERE	NONE	BAF_WEIGHTED	190	0.4674	1	1	0.9024	1.0492`
- B: `chr1	107865001	109193000	6.4838	2	0.6946	0.6946	NONE	NONE	BAF_WEIGHTED	1	0.2812	107394001	108336001	1.9805	4.5033`
- B: `chr1	109193001	123605522	1.9411	7	0.5739	0.5739	NONE	CENTROMERE	BAF_WEIGHTED	21	0.4191	108337001	110049001	0.8271	1.1140`
- B: `chr1	123605523	248956422	1.9754	93	0.5333	0.5062	CENTROMERE	TELOMERE	BAF_WEIGHTED	148	0.4177	123605523	123605523	0.9754	1.0000`
- B: `chr2	1	18304500	1.9603	20	0.5263	0.5101	TELOMERE	NONE	BAF_WEIGHTED	26	0.4452	1	1	0.9603	1.0000`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.purity.range.tsv

lines host=15904, image=15904; only-in-host 15903, only-in-image 15903

- A: `1.0000	0.9563	0.2816	0.9416	2.0400	0.0000`
- A: `0.9900	0.9565	0.2818	0.9416	2.0400	0.0000`
- A: `0.9800	0.9567	0.2819	0.9416	2.0400	0.0000`
- A: `0.9700	0.9569	0.2821	0.9416	2.0400	0.0000`
- A: `0.9600	0.9570	0.2824	0.9416	2.0400	0.0000`
- B: `1.0000	0.9577	0.2812	0.9416	2.0400	0.0000`
- B: `0.9900	0.9579	0.2814	0.9416	2.0400	0.0000`
- B: `0.9800	0.9581	0.2817	0.9416	2.0400	0.0000`
- B: `0.9700	0.9583	0.2819	0.9416	2.0400	0.0000`
- B: `0.9600	0.9585	0.2822	0.9416	2.0400	0.0000`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.purity.tsv

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `1.0000	0.9754	0.2988	0.9416	2.0000	FEMALE	NO_TUMOR	0.0497	0.3100	1.0000	2.0000	2.2200	0.4170	0.9416	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR`
- B: `1.0000	0.9769	0.3010	0.9416	2.0000	FEMALE	NO_TUMOR	0.0497	0.3100	1.0000	2.0000	2.2200	0.4214	0.9416	0.0000	false	0.0000	UNKNOWN	0	UNKNOWN	0.0000	UNKNOWN	0	TUMOR`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.segment.tsv

lines host=206, image=210; only-in-host 124, only-in-image 128

- A: `chr1	1785001	107394000	DIPLOID	false	78	0.5376	0.3611	0.9532	1.0000	1.0000	0.1956	0.3455	1.9546	0.0000	0.0000	1.9546	true	NONE	190	0.5376	0.4674	1.0588	1	178500`
- A: `chr1	107394001	108337000	DIPLOID	false	2	0.6946	0.1000	3.1669	1.0000	1.0000	0.9831	0.0237	6.4934	0.0000	0.0000	6.4934	true	NONE	1	0.6946	0.2812	2.4106	107394001`
- A: `chr1	108337001	119700000	DIPLOID	false	7	0.5739	0.5975	0.9481	1.0000	1.0000	0.4273	0.6901	1.9440	0.0000	0.0000	1.9440	true	NONE	21	0.5739	0.4191	1.1149	10833700`
- A: `chr1	123605523	248361000	DIPLOID	false	93	0.5333	0.1000	0.9648	1.0000	1.0000	0.1000	0.1187	1.9783	0.0000	0.0000	1.9783	true	CENTROMERE	148	0.5055	0.4177	1.0087	`
- A: `chr2	615001	17866000	DIPLOID	false	20	0.5263	0.1426	0.9574	1.0000	1.0000	0.1000	0.1455	1.9632	0.0000	0.0000	1.9632	true	NONE	26	0.5094	0.4452	1.0147	1	615001`
- B: `chr1	1785001	107394000	DIPLOID	false	78	0.5376	0.3663	0.9532	1.0000	1.0000	0.1899	0.3452	1.9517	0.0000	0.0000	1.9517	true	NONE	190	0.5376	0.4674	1.0587	1	178500`
- B: `chr1	107394001	108337000	DIPLOID	false	2	0.6946	0.1000	3.1669	1.0000	1.0000	0.9847	0.0237	6.4838	0.0000	0.0000	6.4838	true	NONE	1	0.6946	0.2812	2.4091	107394001`
- B: `chr1	108337001	119700000	DIPLOID	false	7	0.5739	0.6016	0.9481	1.0000	1.0000	0.4224	0.6895	1.9411	0.0000	0.0000	1.9411	true	NONE	21	0.5739	0.4191	1.1148	10833700`
- B: `chr1	123605523	248361000	DIPLOID	false	93	0.5333	0.1000	0.9648	1.0000	1.0000	0.1000	0.1187	1.9754	0.0000	0.0000	1.9754	true	CENTROMERE	148	0.5062	0.4177	1.0098	`
- B: `chr2	615001	17866000	DIPLOID	false	20	0.5263	0.1539	0.9574	1.0000	1.0000	0.1000	0.1523	1.9603	0.0000	0.0000	1.9603	true	NONE	26	0.5101	0.4452	1.0159	1	615001`

### 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.target_region_cn.tsv

lines host=5317, image=5317; only-in-host 5316, only-in-image 5316

- A: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	24.9800	0.4144	-1.0000	1	107865000	1.9546	0.9038	190	78	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	29.7660	0.4806	-1.0000	1	107865000	1.9546	0.9038	190	78	UNKNOWN	BAF_WEIGHTED`
- A: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1202.4520	0.4701	1.0507	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHT`
- A: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2071.8730	0.3942	1.0354	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHTED`
- A: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	493.0200	0.5037	0.9249	1	107865000	1.9546	0.9038	190	78	DIPLOID	BAF_WEIGHTE`
- B: `chr1	629001	630000	bb.chr1.629966:629967-630086	true	24.9800	0.4144	-1.0000	1	107865000	1.9517	0.9024	190	78	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	630001	631000	bb.chr1.629966:629967-630086	true	29.7660	0.4806	-1.0000	1	107865000	1.9517	0.9024	190	78	UNKNOWN	BAF_WEIGHTED`
- B: `chr1	1785001	1786000	GNB1_exon_12:1785285-1785744;GNB1_exon_12:1785773-1787052	false	1202.4520	0.4701	1.0507	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHT`
- B: `chr1	1786001	1787000	GNB1_exon_12:1785773-1787052	false	2071.8730	0.3942	1.0354	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHTED`
- B: `chr1	1787001	1788000	GNB1_exon_12:1785773-1787052;GNB1_exon_11:1787319-1787438	false	493.0200	0.5037	0.9249	1	107865000	1.9517	0.9024	190	78	DIPLOID	BAF_WEIGHTE`

### 26CGH799-TwistMyVal/qc/26CGH799-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH799-TwistMyVal.final.bam (2564058377 bytes)`
- B: `OK 26CGH799-TwistMyVal.final.bam (2564058366 bytes)`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_hsmetrics.txt

lines host=213, image=213; only-in-host 1, only-in-image 1

- A: `# Started on: Sun Sep 06 15:12:31 GMT 2026`
- B: `# Started on: Thu Sep 10 10:55:32 GMT 2026`

### 26CGH885-TwistMyVal/clinical/cnv/reconcnv/26CGH885-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH885-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH885-TwistMyVal.reconcnv.log

lines host=1, image=15; only-in-host 0, only-in-image 14

- B: `Traceback (most recent call last):`
- B: `  File "/goast/hemat_data/nf-core-tspipe/tools/reconcnv/reconCNV.py", line 16, in <module>`
- B: `    from bokeh.layouts import row, column, layout`
- B: `  File "/opt/envs/reconCNV/lib/python3.6/site-packages/bokeh/layouts.py", line 32, in <module>`
- B: `    from .models.tools import ProxyToolbar, ToolbarBox`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.amber.log

lines host=6, image=6; only-in-host 6, only-in-image 6

- A: `07:18:03.995 [INFO ] Amber version 4.3`
- A: `07:18:07.073 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- A: `07:18:07.696 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- A: `07:18:07.696 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- A: `07:18:09.476 [INFO ] applying PCF segmentation`
- B: `11:00:44.658 [INFO ] Amber version 4.3`
- B: `11:00:47.808 [INFO ] loaded 6345995 Amber germline sites from AmberGermlineSites.38.tsv.gz`
- B: `11:00:48.840 [INFO ] removed 4 blacklisted loci, 9288 remaining`
- B: `11:00:48.841 [INFO ] processing tumor germline heterozygous(9288) and homozygous(0) sites`
- B: `11:00:50.857 [INFO ] applying PCF segmentation`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.cobalt.log

lines host=7, image=7; only-in-host 7, only-in-image 7

- A: `07:18:04.380 [INFO ] Cobalt version 3.0`
- A: `07:18:04.385 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- A: `07:18:04.498 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- A: `07:18:09.605 [INFO ] tumor depths(3088257) collected`
- A: `07:18:10.632 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`
- B: `11:01:30.897 [INFO ] Cobalt version 3.0`
- B: `11:01:30.902 [INFO ] reading GC Profile from GC_profile.1000bp.38.cnp`
- B: `11:01:31.023 [INFO ] calculating read depths from 26CGH885-TwistMyVal.final.bam`
- B: `11:01:36.467 [INFO ] tumor depths(3088257) collected`
- B: `11:01:37.418 [INFO ] loaded 5318 target-panel norm regions from file(target_regions.cobalt_normalisation.twist_myeloid.38.tsv)`

### 26CGH885-TwistMyVal/cnv_hmftools/26CGH885-TwistMyVal.purple.log

lines host=19, image=20; only-in-host 19, only-in-image 20

- A: `08:24:15.716 [INFO ] Purple version 4.4`
- A: `08:24:15.719 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- A: `08:24:15.719 [INFO ] output directory: purple/`
- A: `08:24:15.783 [INFO ] using ref genome: V38`
- A: `08:24:16.974 [INFO ] loaded 4868 target regions bases(total=996878 coding=327383) from file(target_regions.twist_myeloid.38.bed)`
- B: `[0.017s][warning][perf,memops] Cannot use file /tmp/hsperfdata_hemat/44 because it is locked by another process (errno = 11)`
- B: `11:05:28.053 [INFO ] Purple version 4.4`
- B: `11:05:28.056 [INFO ] reference(NONE) tumor(26CGH885-TwistMyVal) running on target-regions only`
- B: `11:05:28.057 [INFO ] output directory: purple/`
- B: `11:05:28.146 [INFO ] using ref genome: V38`

### 26CGH885-TwistMyVal/qc/26CGH885-TwistMyVal.quickcheck.txt

lines host=2, image=2; only-in-host 1, only-in-image 1

- A: `OK 26CGH885-TwistMyVal.final.bam (2617392402 bytes)`
- B: `OK 26CGH885-TwistMyVal.final.bam (2617392391 bytes)`

## Cosmetic-only differences (24)

- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_genebe_cache.json (only-in-host 6, only-in-image 6; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_mobidetails_cache.json (only-in-host 6, only-in-image 6; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_oncokb_cache.json (only-in-host 6, only-in-image 6; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_genebe_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_mobidetails_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_oncokb_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_genebe_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_mobidetails_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_oncokb_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_genebe_cache.json (only-in-host 10, only-in-image 10; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_mobidetails_cache.json (only-in-host 10, only-in-image 10; e.g. `    "_fetched_at": "2026-09-10 07:48 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_oncokb_cache.json (only-in-host 10, only-in-image 10; e.g. `    "_fetched_at": "2026-09-10 07:49 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_genebe_cache.json (only-in-host 17, only-in-image 17; e.g. `    "_fetched_at": "2026-09-10 07:49 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_mobidetails_cache.json (only-in-host 17, only-in-image 17; e.g. `    "_fetched_at": "2026-09-10 07:49 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_oncokb_cache.json (only-in-host 17, only-in-image 17; e.g. `    "_fetched_at": "2026-09-10 07:49 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_genebe_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:49 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_mobidetails_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_oncokb_cache.json (only-in-host 5, only-in-image 5; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_genebe_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_mobidetails_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_oncokb_cache.json (only-in-host 7, only-in-image 7; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_genebe_cache.json (only-in-host 9, only-in-image 9; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_mobidetails_cache.json (only-in-host 9, only-in-image 9; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_oncokb_cache.json (only-in-host 9, only-in-image 9; e.g. `    "_fetched_at": "2026-09-10 07:50 UTC",`)

## Binary / other files that differ by md5 (189)

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
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr1.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr10.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr11.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr12.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr15.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr16.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr17.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr18.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr2.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr20.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr21.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr3.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr4.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr5.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr6.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr7.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr8.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chr9.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.chrX.interleaved.png
- 26CGH1292-TwistMyVal/clinical/cnv/chrom_pages/26CGH1292-TwistMyVal.genome.png
- 26CGH1292-TwistMyVal/clinical/cnv/purple/26CGH1292-TwistMyVal.purple.qc
- 26CGH1292-TwistMyVal/clinical/cnv/reconcnv/26CGH1292-TwistMyVal.reconcnv.html
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr1.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr10.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr11.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr12.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr15.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr16.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr17.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr18.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr2.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr20.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr21.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr3.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr4.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr5.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr6.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr7.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr8.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chr9.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.chrX.interleaved.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH1292-TwistMyVal.genome.png
- 26CGH1292-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH1292-TwistMyVal.reconcnv.html
- 26CGH1292-TwistMyVal/cnv_hmftools/cobalt/26CGH1292-TwistMyVal.cobalt.ratio.pcf
- 26CGH1292-TwistMyVal/cnv_hmftools/purple/26CGH1292-TwistMyVal.purple.qc
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal.rds
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_chromosomes.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_local_optima.pdf
- 26CGH1292-TwistMyVal/purecn/26CGH1292-TwistMyVal_segmentation.pdf
- 26CGH132-TwistMyVal/26CGH132-TwistMyVal_report.zip
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal.final.bam
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal.final.bam.bai
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_fastp.html
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_igv_report.html
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_report.html
- 26CGH132-TwistMyVal/clinical/cnv/reconcnv/26CGH132-TwistMyVal.reconcnv.html
- 26CGH132-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH132-TwistMyVal.reconcnv.html
- 26CGH132-TwistMyVal/cnv_hmftools/amber/26CGH132-TwistMyVal.amber.baf.pcf
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
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal.final.bam.bai
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_fastp.html
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_igv_report.html
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_report.html
- 26CGH60-TwistMyVal/clinical/cnv/reconcnv/26CGH60-TwistMyVal.reconcnv.html
- 26CGH60-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH60-TwistMyVal.reconcnv.html
- 26CGH60-TwistMyVal/cnv_hmftools/amber/26CGH60-TwistMyVal.amber.baf.pcf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal.rds
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_chromosomes.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_local_optima.pdf
- 26CGH60-TwistMyVal/purecn/26CGH60-TwistMyVal_segmentation.pdf
- 26CGH799-TwistMyVal/26CGH799-TwistMyVal_report.zip
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal.final.bam
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal.final.bam.bai
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_fastp.html
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_igv_report.html
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_report.html
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.17p.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr1.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr10.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr11.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr12.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr14.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr2.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr20.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr22.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr3.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr4.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr5.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr6.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr7.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr8.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chr9.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.chrX.interleaved.png
- 26CGH799-TwistMyVal/clinical/cnv/chrom_pages/26CGH799-TwistMyVal.genome.png
- 26CGH799-TwistMyVal/clinical/cnv/purple/26CGH799-TwistMyVal.purple.qc
- 26CGH799-TwistMyVal/clinical/cnv/reconcnv/26CGH799-TwistMyVal.reconcnv.html
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.17p.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr1.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr10.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr11.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr12.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr14.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr2.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr20.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr22.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr3.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr4.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr5.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr6.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr7.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr8.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chr9.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.chrX.interleaved.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/chrom_pages/26CGH799-TwistMyVal.genome.png
- 26CGH799-TwistMyVal/cnv_consensus_multi/reconcnv/26CGH799-TwistMyVal.reconcnv.html
- 26CGH799-TwistMyVal/cnv_hmftools/cobalt/26CGH799-TwistMyVal.cobalt.ratio.pcf
- 26CGH799-TwistMyVal/cnv_hmftools/purple/26CGH799-TwistMyVal.purple.qc
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal.rds
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_chromosomes.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_local_optima.pdf
- 26CGH799-TwistMyVal/purecn/26CGH799-TwistMyVal_segmentation.pdf
- 26CGH885-TwistMyVal/26CGH885-TwistMyVal_report.zip
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal.final.bam
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal.final.bam.bai
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

- only host: 26CGH1043-TwistMyVal/cnv_baf/26CGH1043-TwistMyVal.baf17p.png
- only host: 26CGH1043-TwistMyVal/cnv_baf/26CGH1043-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH1043-TwistMyVal/cnv_baf/26CGH1043-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH1043-TwistMyVal_genome_scatter.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1043-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_AKT1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ALAS2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ANKRD26.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ARID1A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ASXL1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ASXL2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ATM.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BCL11B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BCL2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BCOR.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BCORL1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BIRC3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BPGM.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BRINP3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BTG1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_BTK.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CALR.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CBL.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CBLB.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CCNC.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CCND3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CDKN1B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CDKN2A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CDKN2B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CEBPA.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CSF1R.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CSF3R.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CSMD1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CSNK1A1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CTCF.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CTNNB1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_CUX1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_DDX3X.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_DDX41.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_DHX15.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_DNMT1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_DNMT3A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_EED.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_EGLN1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ELANE.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_EPAS1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_EPOR.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ERG.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ETNK1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ETV6.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_EZH2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_FLT3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_GATA1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_GATA2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_GFI1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_GNAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_GNB1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_HNRNPK.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_HRAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_IKZF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_IL7R.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_IRF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_JAK2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_KDM6A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_KDM6B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_KIT.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_KMT2A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_KRAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_LIG4.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_LUC7L2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MAP2K1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MN1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MPL.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MYB.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MYC.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MYCN.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_MYD88.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NAF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NFE2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NOTCH1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NOTCH3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NPM1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_NRAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PARN.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PAX5.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PHF6.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PIGA.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PLCG2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PPM1D.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PRPF40B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PRPF8.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PTEN.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_PTPN11.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RAD21.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RAD51.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RAD51C.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RIT1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RRAS.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RRAS2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_RUNX1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SAMD9.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SAMD9L.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SETBP1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SETD1B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SETD2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SF3A1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SF3B1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SH2B3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SMC1A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SMC3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SRSF2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_STAG2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_STAT3.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_STAT5B.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_SUZ12.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_TET2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_TP53.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_U2AF1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_U2AF2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_UBA1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_UBE2T.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_UBTF.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_WT1.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_XRCC2.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ZBTB7A.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ZFHX4.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ZNF91.png
- only host: 26CGH1043-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1043-TwistMyVal_ZRSR2.png
- only host: 26CGH1250-TwistMyVal/cnv_baf/26CGH1250-TwistMyVal.baf17p.png
- only host: 26CGH1250-TwistMyVal/cnv_baf/26CGH1250-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH1250-TwistMyVal/cnv_baf/26CGH1250-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH1250-TwistMyVal_genome_scatter.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1250-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_AKT1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ALAS2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ANKRD26.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ARID1A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ASXL1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ASXL2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ATM.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BCL11B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BCL2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BCOR.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BCORL1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BIRC3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BPGM.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BRINP3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BTG1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_BTK.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CALR.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CBL.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CBLB.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CCNC.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CCND3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CDKN1B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CDKN2A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CDKN2B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CEBPA.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CSF1R.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CSF3R.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CSMD1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CSNK1A1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CTCF.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CTNNB1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_CUX1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_DDX3X.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_DDX41.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_DHX15.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_DNMT1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_DNMT3A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_EED.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_EGLN1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ELANE.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_EPAS1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_EPOR.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ERG.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ETNK1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ETV6.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_EZH2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_FLT3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_GATA1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_GATA2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_GFI1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_GNAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_GNB1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_HNRNPK.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_HRAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_IKZF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_IL7R.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_IRF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_JAK2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_KDM6A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_KDM6B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_KIT.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_KMT2A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_KRAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_LIG4.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_LUC7L2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MAP2K1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MN1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MPL.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MYB.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MYC.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MYCN.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_MYD88.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NAF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NFE2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NOTCH1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NOTCH3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NPM1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_NRAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PARN.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PAX5.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PHF6.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PIGA.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PLCG2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PPM1D.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PRPF40B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PRPF8.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PTEN.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_PTPN11.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RAD21.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RAD51.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RAD51C.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RIT1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RRAS.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RRAS2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_RUNX1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SAMD9.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SAMD9L.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SETBP1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SETD1B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SETD2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SF3A1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SF3B1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SH2B3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SMC1A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SMC3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SRSF2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_STAG2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_STAT3.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_STAT5B.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_SUZ12.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_TET2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_TP53.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_U2AF1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_U2AF2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_UBA1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_UBE2T.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_UBTF.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_WT1.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_XRCC2.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ZBTB7A.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ZFHX4.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ZNF91.png
- only host: 26CGH1250-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1250-TwistMyVal_ZRSR2.png
- only host: 26CGH1292-TwistMyVal/cnv_baf/26CGH1292-TwistMyVal.baf17p.png
- only host: 26CGH1292-TwistMyVal/cnv_baf/26CGH1292-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH1292-TwistMyVal/cnv_baf/26CGH1292-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH1292-TwistMyVal_genome_scatter.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1292-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_AKT1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ALAS2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ANKRD26.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ARID1A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ASXL1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ASXL2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ATM.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BCL11B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BCL2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BCOR.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BCORL1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BIRC3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BPGM.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BRINP3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BTG1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_BTK.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CALR.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CBL.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CBLB.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CCNC.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CCND3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CDKN1B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CDKN2A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CDKN2B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CEBPA.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CSF1R.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CSF3R.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CSMD1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CSNK1A1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CTCF.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CTNNB1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_CUX1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_DDX3X.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_DDX41.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_DHX15.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_DNMT1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_DNMT3A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_EED.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_EGLN1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ELANE.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_EPAS1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_EPOR.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ERG.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ETNK1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ETV6.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_EZH2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_FLT3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_GATA1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_GATA2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_GFI1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_GNAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_GNB1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_HNRNPK.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_HRAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_IKZF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_IL7R.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_IRF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_JAK2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_KDM6A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_KDM6B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_KIT.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_KMT2A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_KRAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_LIG4.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_LUC7L2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MAP2K1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MN1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MPL.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MYB.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MYC.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MYCN.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_MYD88.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NAF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NFE2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NOTCH1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NOTCH3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NPM1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_NRAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PARN.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PAX5.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PHF6.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PIGA.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PLCG2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PPM1D.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PRPF40B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PRPF8.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PTEN.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_PTPN11.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RAD21.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RAD51.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RAD51C.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RIT1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RRAS.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RRAS2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_RUNX1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SAMD9.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SAMD9L.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SETBP1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SETD1B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SETD2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SF3A1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SF3B1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SH2B3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SMC1A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SMC3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SRSF2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_STAG2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_STAT3.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_STAT5B.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_SUZ12.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_TET2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_TP53.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_U2AF1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_U2AF2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_UBA1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_UBE2T.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_UBTF.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_WT1.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_XRCC2.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ZBTB7A.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ZFHX4.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ZNF91.png
- only host: 26CGH1292-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1292-TwistMyVal_ZRSR2.png
- only host: 26CGH132-TwistMyVal/cnv_baf/26CGH132-TwistMyVal.baf17p.png
- only host: 26CGH132-TwistMyVal/cnv_baf/26CGH132-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH132-TwistMyVal/cnv_baf/26CGH132-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH132-TwistMyVal_genome_scatter.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH132-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_AKT1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ALAS2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ANKRD26.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ARID1A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ASXL1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ASXL2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ATM.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BCL11B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BCL2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BCOR.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BCORL1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BIRC3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BPGM.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BRINP3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BTG1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_BTK.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CALR.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CBL.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CBLB.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CCNC.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CCND3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CDKN1B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CDKN2A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CDKN2B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CEBPA.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CSF1R.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CSF3R.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CSMD1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CSNK1A1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CTCF.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CTNNB1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_CUX1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_DDX3X.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_DDX41.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_DHX15.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_DNMT1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_DNMT3A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_EED.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_EGLN1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ELANE.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_EPAS1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_EPOR.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ERG.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ETNK1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ETV6.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_EZH2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_FLT3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_GATA1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_GATA2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_GFI1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_GNAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_GNB1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_HNRNPK.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_HRAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_IKZF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_IL7R.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_IRF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_JAK2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_KDM6A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_KDM6B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_KIT.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_KMT2A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_KRAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_LIG4.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_LUC7L2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MAP2K1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MN1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MPL.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MYB.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MYC.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MYCN.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_MYD88.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NAF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NFE2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NOTCH1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NOTCH3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NPM1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_NRAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PARN.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PAX5.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PHF6.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PIGA.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PLCG2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PPM1D.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PRPF40B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PRPF8.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PTEN.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_PTPN11.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RAD21.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RAD51.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RAD51C.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RIT1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RRAS.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RRAS2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_RUNX1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SAMD9.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SAMD9L.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SETBP1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SETD1B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SETD2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SF3A1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SF3B1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SH2B3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SMC1A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SMC3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SRSF2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_STAG2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_STAT3.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_STAT5B.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_SUZ12.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_TET2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_TP53.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_U2AF1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_U2AF2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_UBA1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_UBE2T.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_UBTF.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_WT1.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_XRCC2.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ZBTB7A.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ZFHX4.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ZNF91.png
- only host: 26CGH132-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH132-TwistMyVal_ZRSR2.png
- only host: 26CGH1480-TwistMyVal/cnv_baf/26CGH1480-TwistMyVal.baf17p.png
- only host: 26CGH1480-TwistMyVal/cnv_baf/26CGH1480-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH1480-TwistMyVal/cnv_baf/26CGH1480-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH1480-TwistMyVal_genome_scatter.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH1480-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_AKT1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ALAS2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ANKRD26.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ARID1A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ASXL1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ASXL2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ATM.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BCL11B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BCL2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BCOR.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BCORL1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BIRC3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BPGM.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BRINP3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BTG1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_BTK.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CALR.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CBL.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CBLB.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CCNC.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CCND3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CDKN1B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CDKN2A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CDKN2B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CEBPA.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CSF1R.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CSF3R.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CSMD1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CSNK1A1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CTCF.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CTNNB1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_CUX1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_DDX3X.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_DDX41.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_DHX15.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_DNMT1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_DNMT3A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_EED.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_EGLN1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ELANE.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_EPAS1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_EPOR.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ERG.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ETNK1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ETV6.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_EZH2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_FLT3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_GATA1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_GATA2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_GFI1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_GNAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_GNB1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_HNRNPK.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_HRAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_IKZF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_IL7R.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_IRF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_JAK2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_KDM6A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_KDM6B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_KIT.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_KMT2A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_KRAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_LIG4.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_LUC7L2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MAP2K1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MN1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MPL.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MYB.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MYC.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MYCN.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_MYD88.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NAF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NFE2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NOTCH1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NOTCH3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NPM1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_NRAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PARN.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PAX5.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PHF6.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PIGA.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PLCG2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PPM1D.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PRPF40B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PRPF8.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PTEN.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_PTPN11.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RAD21.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RAD51.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RAD51C.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RIT1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RRAS.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RRAS2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_RUNX1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SAMD9.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SAMD9L.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SETBP1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SETD1B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SETD2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SF3A1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SF3B1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SH2B3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SMC1A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SMC3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SRSF2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_STAG2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_STAT3.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_STAT5B.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_SUZ12.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_TET2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_TP53.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_U2AF1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_U2AF2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_UBA1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_UBE2T.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_UBTF.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_WT1.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_XRCC2.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ZBTB7A.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ZFHX4.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ZNF91.png
- only host: 26CGH1480-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH1480-TwistMyVal_ZRSR2.png
- only host: 26CGH60-TwistMyVal/cnv_baf/26CGH60-TwistMyVal.baf17p.png
- only host: 26CGH60-TwistMyVal/cnv_baf/26CGH60-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH60-TwistMyVal/cnv_baf/26CGH60-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH60-TwistMyVal_genome_scatter.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH60-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_AKT1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ALAS2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ANKRD26.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ARID1A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ASXL1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ASXL2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ATM.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BCL11B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BCL2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BCOR.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BCORL1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BIRC3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BPGM.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BRINP3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BTG1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_BTK.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CALR.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CBL.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CBLB.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CCNC.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CCND3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CDKN1B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CDKN2A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CDKN2B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CEBPA.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CSF1R.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CSF3R.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CSMD1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CSNK1A1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CTCF.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CTNNB1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_CUX1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_DDX3X.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_DDX41.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_DHX15.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_DNMT1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_DNMT3A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_EED.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_EGLN1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ELANE.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_EPAS1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_EPOR.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ERG.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ETNK1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ETV6.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_EZH2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_FLT3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_GATA1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_GATA2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_GFI1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_GNAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_GNB1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_HNRNPK.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_HRAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_IKZF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_IL7R.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_IRF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_JAK2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_KDM6A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_KDM6B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_KIT.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_KMT2A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_KRAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_LIG4.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_LUC7L2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MAP2K1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MN1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MPL.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MYB.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MYC.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MYCN.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_MYD88.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NAF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NFE2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NOTCH1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NOTCH3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NPM1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_NRAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PARN.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PAX5.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PHF6.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PIGA.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PLCG2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PPM1D.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PRPF40B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PRPF8.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PTEN.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_PTPN11.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RAD21.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RAD51.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RAD51C.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RIT1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RRAS.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RRAS2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_RUNX1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SAMD9.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SAMD9L.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SETBP1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SETD1B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SETD2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SF3A1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SF3B1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SH2B3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SMC1A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SMC3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SRSF2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_STAG2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_STAT3.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_STAT5B.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_SUZ12.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_TET2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_TP53.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_U2AF1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_U2AF2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_UBA1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_UBE2T.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_UBTF.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_WT1.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_XRCC2.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ZBTB7A.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ZFHX4.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ZNF91.png
- only host: 26CGH60-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH60-TwistMyVal_ZRSR2.png
- only host: 26CGH799-TwistMyVal/cnv_baf/26CGH799-TwistMyVal.baf17p.png
- only host: 26CGH799-TwistMyVal/cnv_baf/26CGH799-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH799-TwistMyVal/cnv_baf/26CGH799-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH799-TwistMyVal_genome_scatter.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH799-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_AKT1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ALAS2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ANKRD26.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ARID1A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ASXL1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ASXL2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ATM.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BCL11B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BCL2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BCOR.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BCORL1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BIRC3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BPGM.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BRINP3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BTG1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_BTK.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CALR.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CBL.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CBLB.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CCNC.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CCND3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CDKN1B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CDKN2A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CDKN2B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CEBPA.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CSF1R.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CSF3R.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CSMD1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CSNK1A1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CTCF.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CTNNB1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_CUX1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_DDX3X.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_DDX41.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_DHX15.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_DNMT1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_DNMT3A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_EED.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_EGLN1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ELANE.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_EPAS1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_EPOR.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ERG.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ETNK1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ETV6.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_EZH2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_FLT3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_GATA1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_GATA2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_GFI1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_GNAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_GNB1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_HNRNPK.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_HRAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_IKZF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_IL7R.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_IRF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_JAK2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_KDM6A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_KDM6B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_KIT.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_KMT2A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_KRAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_LIG4.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_LUC7L2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MAP2K1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MN1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MPL.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MYB.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MYC.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MYCN.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_MYD88.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NAF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NFE2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NOTCH1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NOTCH3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NPM1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_NRAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PARN.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PAX5.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PHF6.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PIGA.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PLCG2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PPM1D.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PRPF40B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PRPF8.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PTEN.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_PTPN11.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RAD21.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RAD51.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RAD51C.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RIT1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RRAS.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RRAS2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_RUNX1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SAMD9.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SAMD9L.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SETBP1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SETD1B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SETD2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SF3A1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SF3B1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SH2B3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SMC1A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SMC3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SRSF2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_STAG2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_STAT3.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_STAT5B.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_SUZ12.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_TET2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_TP53.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_U2AF1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_U2AF2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_UBA1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_UBE2T.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_UBTF.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_WT1.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_XRCC2.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ZBTB7A.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ZFHX4.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ZNF91.png
- only host: 26CGH799-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH799-TwistMyVal_ZRSR2.png
- only host: 26CGH885-TwistMyVal/cnv_baf/26CGH885-TwistMyVal.baf17p.png
- only host: 26CGH885-TwistMyVal/cnv_baf/26CGH885-TwistMyVal.baf17p.sites.tsv
- only host: 26CGH885-TwistMyVal/cnv_baf/26CGH885-TwistMyVal.baf17p.summary.tsv
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/overview/26CGH885-TwistMyVal_genome_scatter.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr10_ANKRD26_PTEN_SMC3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr11_ATM_BIRC3_CBL_EED_HRAS_+4.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr12_BTG1_CDKN1B_ETNK1_ETV6_KRAS_+5.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr13_FLT3_LIG4.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr14_AKT1_BCL11B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr15_MAP2K1_RAD51.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr16_CTCF_PARN_PLCG2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr17_KDM6B_NF1_PPM1D_PRPF8_RAD51C_+6.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr18_BCL2_SETBP1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr19_CALR_CEBPA_DNMT1_ELANE_EPOR_+5.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr1_ARID1A_BRINP3_CSF3R_EGLN1_GFI1_+5.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr20_ASXL1_GNAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr21_ERG_RUNX1_U2AF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr22_MN1_SF3A1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr2_ASXL2_DNMT3A_EPAS1_MYCN_SF3B1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr3_CBLB_CTNNB1_GATA2_MYD88_SETD2_+1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr4_DHX15_KIT_NAF1_TET2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr5_CSF1R_CSNK1A1_DDX41_IL7R_IRF1_+1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr6_CCNC_CCND3_MYB.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr7_BPGM_CUX1_EZH2_IKZF1_LUC7L2_+3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr8_CSMD1_MYC_RAD21_ZFHX4.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chr9_CDKN2A_CDKN2B_HNRNPK_JAK2_NOTCH1_+1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_chromosome/26CGH885-TwistMyVal_chrX_ALAS2_BCOR_BCORL1_BTK_DDX3X_+8.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_AKT1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ALAS2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ANKRD26.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ARID1A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ASXL1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ASXL2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ATM.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BCL11B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BCL2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BCOR.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BCORL1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BIRC3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BPGM.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BRINP3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BTG1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_BTK.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CALR.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CBL.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CBLB.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CCNC.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CCND3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CDKN1B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CDKN2A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CDKN2B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CEBPA.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CSF1R.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CSF3R.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CSMD1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CSNK1A1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CTCF.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CTNNB1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_CUX1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_DDX3X.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_DDX41.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_DHX15.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_DNMT1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_DNMT3A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_EED.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_EGLN1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ELANE.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_EPAS1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_EPOR.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ERG.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ETNK1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ETV6.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_EZH2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_FLT3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_GATA1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_GATA2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_GFI1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_GNAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_GNB1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_HNRNPK.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_HRAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_IKZF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_IL7R.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_IRF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_JAK2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_KDM6A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_KDM6B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_KIT.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_KMT2A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_KRAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_LIG4.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_LUC7L2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MAP2K1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MN1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MPL.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MYB.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MYC.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MYCN.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_MYD88.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NAF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NFE2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NOTCH1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NOTCH3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NPM1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_NRAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PARN.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PAX5.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PHF6.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PIGA.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PLCG2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PPM1D.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PRPF40B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PRPF8.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PTEN.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_PTPN11.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RAD21.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RAD51.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RAD51C.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RIT1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RRAS.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RRAS2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_RUNX1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SAMD9.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SAMD9L.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SETBP1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SETD1B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SETD2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SF3A1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SF3B1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SH2B3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SMC1A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SMC3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SRSF2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_STAG2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_STAT3.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_STAT5B.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_SUZ12.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_TET2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_TP53.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_U2AF1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_U2AF2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_UBA1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_UBE2T.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_UBTF.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_WT1.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_XRCC2.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ZBTB7A.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ZFHX4.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ZNF91.png
- only host: 26CGH885-TwistMyVal/cnv_consensus_multi/styled_scatter/per_gene/26CGH885-TwistMyVal_ZRSR2.png
- only host: figures/26CGH1250.17p.grouped.png
- only host: figures/26CGH1250.17p.interleaved.png
- only host: figures/26CGH1250.17p.png
- only host: figures/26CGH1250.17p.targets.png
- only host: figures/26CGH1250.9p.grouped.png
- only host: figures/26CGH1250.9p.interleaved.png
- only host: figures/26CGH1250.9p.png
- only host: figures/26CGH1250.9p.targets.png
- only host: figures/26CGH1250.chr21.grouped.png
- only host: figures/26CGH1250.chr21.interleaved.png
- only host: figures/26CGH1250.chr21.png
- only host: figures/26CGH1250.chr21.targets.png
- only host: figures/26CGH1250.chr7.interleaved.png
- only host: figures/26CGH1250.genes_CDKN2A_CDKN2B_IKZF1_KDM6B_PAX5_TP53.targets.png
- only host: figures/26CGH1250.genes_TP53.png
- only host: figures/26CGH1250.sunrise.png
- only host: figures/26CGH1250.trio.png
- only host: figures/26CGH60.17p.grouped.png
- only host: figures/26CGH60.17p.interleaved.png
- only host: figures/26CGH60.17p.png
- only host: figures/26CGH60.17p.targets.png
- only host: figures/26CGH60.9p.grouped.png
- only host: figures/26CGH60.9p.interleaved.png
- only host: figures/26CGH60.9p.png
- only host: figures/26CGH60.9p.targets.png
- only host: figures/26CGH60.chr21.grouped.png
- only host: figures/26CGH60.chr21.interleaved.png
- only host: figures/26CGH60.chr21.png
- only host: figures/26CGH60.chr21.targets.png
- only host: figures/26CGH60.chr7.interleaved.png
- only host: figures/26CGH60.genes_CDKN2A_CDKN2B_IKZF1_KDM6B_PAX5_TP53.targets.png
- only host: figures/26CGH60.genes_TP53.png
- only host: figures/26CGH60.sunrise.png
- only host: figures/26CGH60.trio.png
- only host: figures/26CGH60_chroms/26CGH60.chr1.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr10.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr11.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr12.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr13.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr14.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr15.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr16.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr17.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr18.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr19.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr2.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr20.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr21.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr22.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr3.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr4.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr5.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr6.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr7.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr8.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chr9.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chrX.interleaved.png
- only host: figures/26CGH60_chroms/26CGH60.chrY.interleaved.png
- only host: tspipe_run8_reports.zip
- only image: tspipe_run8_img_reports.zip

