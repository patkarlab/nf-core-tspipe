# Run comparison: gandalf (/goast/hemat_data/twist_val/tspipe_run8_img11) vs clinical23 (/goast/hemat_data/twist_val/tspipe_run8_c23) -- 2026-09-11

Files: 1386 common, 9 only in gandalf, 1 only in clinical23. Common: 1201 identical (md5), 185 differ (66 real text differences, 10 cosmetic-only text differences, 109 binary/other).

Cosmetic = the differing lines match after masking paths, dates, run names, session ids and task hashes.

| Top-level dir | identical | real diff | cosmetic diff | binary diff |
|---|---|---|---|---|
| 26CGH1043-TwistMyVal | 151 | 9 | 1 | 14 |
| 26CGH1250-TwistMyVal | 159 | 9 | 1 | 14 |
| 26CGH1292-TwistMyVal | 143 | 9 | 1 | 14 |
| 26CGH132-TwistMyVal | 143 | 6 | 3 | 13 |
| 26CGH1480-TwistMyVal | 149 | 9 | 1 | 14 |
| 26CGH60-TwistMyVal | 145 | 8 | 1 | 13 |
| 26CGH799-TwistMyVal | 149 | 8 | 1 | 13 |
| 26CGH885-TwistMyVal | 149 | 8 | 1 | 13 |
| assets | 13 | 0 | 0 | 0 |
| cohort_index.html | 0 | 0 | 0 | 1 |

## Real text differences (66)

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=7, clinical23=8; only-in-gandalf 6, only-in-clinical23 7

- A: `26CGH1043-TwistMyVal	chr1	26696528	26696528	C	G	ARID1A	missense_variant	ENST00000324856.13:c.125C>G	ENSP00000320485.7:p.Ala42Gly	chr1:g.26696528C>G	NM_006015.6:`
- A: `26CGH1043-TwistMyVal	chr13	28034141	28034141	T	C	FLT3	missense_variant	ENST00000241453.12:c.1778A>G	ENSP00000241453.7:p.Asp593Gly	chr13:g.28034141T>C	NM_004119.`
- A: `26CGH1043-TwistMyVal	chrX	45083507	45083507	G	C	KDM6A	missense_variant	ENST00000611820.5:c.3488G>C	ENSP00000483595.2:p.Arg1163Pro	chrX:g.45083507G>C	NM_00129141`
- A: `26CGH1043-TwistMyVal	chr4	105276156	105276156	C	T	TET2	synonymous_variant	ENST00000380013.9:c.5646C>T	ENSP00000369351.4:p.Ala1882%3D	chr4:g.105276156C>T	NM_0011`
- A: `26CGH1043-TwistMyVal	chr8	76778391	76778391	A	G	ZFHX4	missense_variant	ENST00000651372.2:c.3277A>G	ENSP00000498627.1:p.Asn1093Asp	chr8:g.76778391A>G	NM_024721.5`
- B: `26CGH1043-TwistMyVal	chr1	26696528	26696528	C	G	ARID1A	missense_variant	ENST00000324856.13:c.125C>G	ENSP00000320485.7:p.Ala42Gly	chr1:g.26696528C>G	NM_006015.6:`
- B: `26CGH1043-TwistMyVal	chr13	28034141	28034141	T	C	FLT3	missense_variant	ENST00000241453.12:c.1778A>G	ENSP00000241453.7:p.Asp593Gly	chr13:g.28034141T>C	NM_004119.`
- B: `26CGH1043-TwistMyVal	chrX	45083507	45083507	G	C	KDM6A	missense_variant	ENST00000611820.5:c.3488G>C	ENSP00000483595.2:p.Arg1163Pro	chrX:g.45083507G>C	NM_00129141`
- B: `26CGH1043-TwistMyVal	chr22	27798942	27798942	C	T	MN1	synonymous_variant	ENST00000302326.5:c.1602G>A	ENSP00000304956.4:p.Gln534%3D	chr22:g.27798942C>T	NM_002430.`
- B: `26CGH1043-TwistMyVal	chr4	105276156	105276156	C	T	TET2	synonymous_variant	ENST00000380013.9:c.5646C>T	ENSP00000369351.4:p.Ala1882%3D	chr4:g.105276156C>T	NM_0011`

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5279, clinical23=5385; only-in-gandalf 12, only-in-clinical23 118

- A: `26CGH1043-TwistMyVal	chr10	125426040	125426040	A	C	-1	intergenic_variant	-1	-1	MODIFIER	1	VarDict	1356	75	5.24	REJECT	-1	-1	-1	-1	-1	-1	0.0883	0.1611	rs77300345`
- A: `26CGH1043-TwistMyVal	chr14	54617471	54617471	C	CT	SAMD4A	intron_variant	ENST00000554335.6:c.196+49368dup	-1	MODIFIER	1	VarDict	1624	60	3.56	REJECT	-1	-1	-1	-1	-`
- A: `26CGH1043-TwistMyVal	chr14	99175588	99175588	G	C	BCL11B	synonymous_variant	ENST00000357195.8:c.1248C>G	ENSP00000349723.3:p.Gly416%3D	LOW	1	FreeBayes	1539	135	8.`
- A: `26CGH1043-TwistMyVal	chr16	29317074	29317074	C	T	-1	intron_variant&non_coding_transcript_variant	ENST00000604430.1:n.1000-3854C>T	-1	MODIFIER	1	Mutect2	1359	25	`
- A: `26CGH1043-TwistMyVal	chr17	44207116	44207116	A	T	UBTF	3_prime_UTR_variant	ENST00000436088.6:c.*126T>A	-1	MODIFIER	1	VarDict	1283	42	3.17	REJECT	-1	-1	-1	-1	-1	-`
- B: `26CGH1043-TwistMyVal	chr10	110577501	110577502	CT	C	SMC3	intron_variant	ENST00000361804.5:c.270+18del	-1	MODIFIER	1	VarScan	911	29	3.09	REJECT	-1	-1	-1	-1	-1	-1`
- B: `26CGH1043-TwistMyVal	chr10	125426040	125426040	A	C	-1	intergenic_variant	-1	-1	MODIFIER	2	VarScan,VarDict	1356	75	5.24	REJECT	-1	-1	-1	-1	-1	-1	0.0883	0.1611	rs`
- B: `26CGH1043-TwistMyVal	chr10	132512538	132512538	A	G	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-377T>C	-1	MODIFIER	1	VarScan	1011	40	`
- B: `26CGH1043-TwistMyVal	chr10	132512630	132512630	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-469C>T	-1	MODIFIER	1	VarScan	2068	54	`
- B: `26CGH1043-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	2`

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_genebe_cache.json

lines gandalf=98, clinical23=114; only-in-gandalf 6, only-in-clinical23 16

- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `  "chr22:27798942:C:T": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:14:48 GMT 2026`
- B: `# Started on: Fri Sep 11 02:42:33 GMT 2026`

### 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_mobidetails_cache.json

lines gandalf=680, clinical23=902; only-in-gandalf 6, only-in-clinical23 97

- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `  "chr22:27798942:C:T": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`

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

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=6, clinical23=9; only-in-gandalf 5, only-in-clinical23 8

- A: `26CGH1250-TwistMyVal	chr1	190098163	190098163	C	T	BRINP3	missense_variant	ENST00000367462.5:c.2156G>A	ENSP00000356432.3:p.Arg719His	chr1:g.190098163C>T	NM_19905`
- A: `26CGH1250-TwistMyVal	chr22	27799838	27799838	G	T	MN1	missense_variant	ENST00000302326.5:c.706C>A	ENSP00000304956.4:p.Pro236Thr	chr22:g.27799838G>T	NM_002430.3:c`
- A: `26CGH1250-TwistMyVal	chr12	112450359	112450359	G	T	PTPN11	missense_variant	ENST00000351677.7:c.179G>T	ENSP00000340944.3:p.Gly60Val	chr12:g.112450359G>T	NM_00283`
- A: `26CGH1250-TwistMyVal	chr3	47120336	47120336	C	G	SETD2	missense_variant	ENST00000409792.4:c.4300G>C	ENSP00000386759.3:p.Gly1434Arg	chr3:g.47120336C>G	NM_014159.7`
- A: `26CGH1250-TwistMyVal	chr8	76852272	76852272	C	A	ZFHX4	missense_variant	ENST00000651372.2:c.5351C>A	ENSP00000498627.1:p.Thr1784Asn	chr8:g.76852272C>A	NM_024721.5`
- B: `26CGH1250-TwistMyVal	chr1	26696967	26696967	C	G	ARID1A	synonymous_variant	ENST00000324856.13:c.564C>G	ENSP00000320485.7:p.Gly188%3D	chr1:g.26696967C>G	NM_006015`
- B: `26CGH1250-TwistMyVal	chr1	190098163	190098163	C	T	BRINP3	missense_variant	ENST00000367462.5:c.2156G>A	ENSP00000356432.3:p.Arg719His	chr1:g.190098163C>T	NM_19905`
- B: `26CGH1250-TwistMyVal	chr11	119206533	119206533	A	C	CBL	missense_variant	ENST00000264033.6:c.116A>C	ENSP00000264033.3:p.His39Pro	chr11:g.119206533A>C	NM_005188.4`
- B: `26CGH1250-TwistMyVal	chr22	27797803	27797803	T	C	MN1	missense_variant	ENST00000302326.5:c.2741A>G	ENSP00000304956.4:p.Asp914Gly	chr22:g.27797803T>C	NM_002430.3:`
- B: `26CGH1250-TwistMyVal	chr22	27799838	27799838	G	T	MN1	missense_variant	ENST00000302326.5:c.706C>A	ENSP00000304956.4:p.Pro236Thr	chr22:g.27799838G>T	NM_002430.3:c`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5302, clinical23=5392; only-in-gandalf 15, only-in-clinical23 105

- A: `26CGH1250-TwistMyVal	chr11	119206533	119206533	A	C	CBL	missense_variant	ENST00000264033.6:c.116A>C	ENSP00000264033.3:p.His39Pro	MODERATE	1	FreeBayes	1295	101	7.`
- A: `26CGH1250-TwistMyVal	chr12	121831757	121831757	G	C	SETD1B	3_prime_UTR_variant	ENST00000604567.6:c.*1518G>C	-1	MODIFIER	1	FreeBayes	1315	160	10.8	REJECT	-1	-1	-1`
- A: `26CGH1250-TwistMyVal	chr14	99172041	99172041	G	GA	BCL11B	3_prime_UTR_variant	ENST00000357195.8:c.*2109dup	-1	MODIFIER	1	VarDict	1902	60	3.06	REJECT	-1	-1	-1	-1	`
- A: `26CGH1250-TwistMyVal	chr14	99175588	99175588	G	C	BCL11B	synonymous_variant	ENST00000357195.8:c.1248C>G	ENSP00000349723.3:p.Gly416%3D	LOW	1	FreeBayes	2076	161	7.`
- A: `26CGH1250-TwistMyVal	chr17	30646769	30646770	CG	C	-1	intron_variant&non_coding_transcript_variant	ENST00000578265.5:n.288-1595del	-1	MODIFIER	1	VarDict	1347	41	`
- B: `26CGH1250-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	1`
- B: `26CGH1250-TwistMyVal	chr10	87965473	87965474	AT	A	PTEN	3_prime_UTR_variant	ENST00000371953.8:c.*10del	-1	MODIFIER	1	VarScan	1088	40	3.55	REJECT	-1	Uncertain_sig`
- B: `26CGH1250-TwistMyVal	chr10	87966827	87966828	CA	C	PTEN	3_prime_UTR_variant	ENST00000371953.8:c.*1363del	-1	MODIFIER	1	VarScan	1137	31	2.65	REJECT	-1	-1	-1	-1	-1`
- B: `26CGH1250-TwistMyVal	chr11	102321868	102321868	A	AT	BIRC3	5_prime_UTR_variant	ENST00000263464.9:c.-2633dup	-1	MODIFIER	1	VarScan	1108	27	2.38	REJECT	-1	-1	-1	-1`
- B: `26CGH1250-TwistMyVal	chr11	118525622	118525622	G	GA	KMT2A	3_prime_UTR_variant	ENST00000534358.8:c.*3459dup	-1	MODIFIER	1	VarScan	973	25	2.51	REJECT	-1	-1	-1	-1	`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_genebe_cache.json

lines gandalf=82, clinical23=130; only-in-gandalf 5, only-in-clinical23 27

- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- B: `  "chr11:119206533:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "acmg_criteria": "PM2",`
- B: `    "acmg_score": 2,`
- B: `    "clinvar_disease": "Hereditary cancer",`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:16:30 GMT 2026`
- B: `# Started on: Fri Sep 11 02:46:07 GMT 2026`

### 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_mobidetails_cache.json

lines gandalf=260, clinical23=278; only-in-gandalf 5, only-in-clinical23 17

- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:28 UTC",`
- B: `  "chr11:119206533:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "hgvs_g": "NC_000011.10:g.119206533A>C",`
- B: `    "warning": "The variant NC_000011.10:g.119206533A>C does not exist yet in MD"`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`

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

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=8, clinical23=10; only-in-gandalf 7, only-in-clinical23 9

- A: `26CGH1292-TwistMyVal	chr2	46378051	46378051	C	A	EPAS1	synonymous_variant	ENST00000263734.5:c.1407C>A	ENSP00000263734.3:p.Thr469%3D	chr2:g.46378051C>A	NM_001430.`
- A: `26CGH1292-TwistMyVal	chr12	22673582	22673582	A	T	ETNK1	missense_variant	ENST00000266517.9:c.867A>T	ENSP00000266517.4:p.Lys289Asn	chr12:g.22673582A>T	NM_018638.5`
- A: `26CGH1292-TwistMyVal	chr5	35874462	35874472	TATCTTACTAA	T	IL7R	frameshift_variant	ENST00000303115.8:c.721_730del	ENSP00000306157.3:p.Ile241ProfsTer5	chr5:g.3587`
- A: `26CGH1292-TwistMyVal	chr22	27799618	27799618	T	TGCTGCTGCTGCTGCTGGG	MN1	inframe_insertion	ENST00000302326.5:c.908_925dup	ENSP00000304956.4:p.Pro303_Gln308dup	chr`
- A: `26CGH1292-TwistMyVal	chr9	37015168	37015168	G	C	PAX5	missense_variant	ENST00000358127.9:c.239C>G	ENSP00000350844.4:p.Pro80Arg	chr9:g.37015168G>C	NM_016734.3:c.2`
- B: `26CGH1292-TwistMyVal	chr1	26696967	26696967	C	G	ARID1A	synonymous_variant	ENST00000324856.13:c.564C>G	ENSP00000320485.7:p.Gly188%3D	chr1:g.26696967C>G	NM_006015`
- B: `26CGH1292-TwistMyVal	chr2	46378051	46378051	C	A	EPAS1	synonymous_variant	ENST00000263734.5:c.1407C>A	ENSP00000263734.3:p.Thr469%3D	chr2:g.46378051C>A	NM_001430.`
- B: `26CGH1292-TwistMyVal	chr12	22673582	22673582	A	T	ETNK1	missense_variant	ENST00000266517.9:c.867A>T	ENSP00000266517.4:p.Lys289Asn	chr12:g.22673582A>T	NM_018638.5`
- B: `26CGH1292-TwistMyVal	chr5	35874462	35874472	TATCTTACTAA	T	IL7R	frameshift_variant	ENST00000303115.8:c.721_730del	ENSP00000306157.3:p.Ile241ProfsTer5	chr5:g.3587`
- B: `26CGH1292-TwistMyVal	chr22	27797803	27797803	T	C	MN1	missense_variant	ENST00000302326.5:c.2741A>G	ENSP00000304956.4:p.Asp914Gly	chr22:g.27797803T>C	NM_002430.3:`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5275, clinical23=5379; only-in-gandalf 19, only-in-clinical23 123

- A: `26CGH1292-TwistMyVal	chr10	38249880	38249880	A	AT	PLD5P1	intron_variant&NMD_transcript_variant	ENST00000640275.1:c.*789+1824dup	-1	MODIFIER	1	VarDict	1122	38	3.`
- A: `26CGH1292-TwistMyVal	chr11	119206539	119206539	A	C	CBL	missense_variant	ENST00000264033.6:c.122A>C	ENSP00000264033.3:p.His41Pro	MODERATE	1	FreeBayes	1314	117	8.`
- A: `26CGH1292-TwistMyVal	chr12	121831757	121831757	G	C	SETD1B	3_prime_UTR_variant	ENST00000604567.6:c.*1518G>C	-1	MODIFIER	1	FreeBayes	1546	185	10.7	REJECT	-1	-1	-1`
- A: `26CGH1292-TwistMyVal	chr12	64992638	64992639	AG	A	LINC02389	downstream_gene_variant	-1	-1	MODIFIER	1	VarDict	1457	54	3.57	REJECT	-1	-1	-1	-1	-1	-1	-1	-1	rs36922`
- A: `26CGH1292-TwistMyVal	chr14	99175588	99175588	G	C	BCL11B	synonymous_variant	ENST00000357195.8:c.1248C>G	ENSP00000349723.3:p.Gly416%3D	LOW	1	FreeBayes	1761	114	6.`
- B: `26CGH1292-TwistMyVal	chr10	110577501	110577502	CT	C	SMC3	intron_variant	ENST00000361804.5:c.270+18del	-1	MODIFIER	1	VarScan	932	26	2.71	REJECT	-1	-1	-1	-1	-1	-1`
- B: `26CGH1292-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	1`
- B: `26CGH1292-TwistMyVal	chr10	38249880	38249880	A	AT	PLD5P1	intron_variant&NMD_transcript_variant	ENST00000640275.1:c.*789+1824dup	-1	MODIFIER	2	VarScan,VarDict	11`
- B: `26CGH1292-TwistMyVal	chr10	55127000	55127001	GT	G	PCDH15	intron_variant	ENST00000613346.4:c.-80+39575del	-1	MODIFIER	1	VarScan	1041	24	2.25	REJECT	-1	-1	-1	-1	-`
- B: `26CGH1292-TwistMyVal	chr10	87965473	87965474	AT	A	PTEN	3_prime_UTR_variant	ENST00000371953.8:c.*10del	-1	MODIFIER	1	VarScan	1347	35	2.53	REJECT	-1	Uncertain_sig`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_genebe_cache.json

lines gandalf=114, clinical23=146; only-in-gandalf 7, only-in-clinical23 20

- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `  "chr1:26696967:C:G": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:16:43 GMT 2026`
- B: `# Started on: Fri Sep 11 02:44:05 GMT 2026`

### 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_mobidetails_cache.json

lines gandalf=908, clinical23=920; only-in-gandalf 7, only-in-clinical23 15

- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `  "chr1:26696967:C:G": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`

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

### 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=11, clinical23=11; only-in-gandalf 9, only-in-clinical23 9

- A: `26CGH132-TwistMyVal	chr20	32435819	32435819	A	G	ASXL1	missense_variant	ENST00000375687.10:c.3107A>G	ENSP00000364839.4:p.Asn1036Ser	chr20:g.32435819A>G	NM_015338`
- A: `26CGH132-TwistMyVal	chr8	2974569	2974569	C	T	CSMD1	synonymous_variant	ENST00000635120.2:c.8622G>A	ENSP00000489225.1:p.Leu2874%3D	chr8:g.2974569C>T	NM_033225.6:c`
- A: `26CGH132-TwistMyVal	chr8	3029439	3029439	C	T	CSMD1	missense_variant	ENST00000635120.2:c.7735G>A	ENSP00000489225.1:p.Glu2579Lys	chr8:g.3029439C>T	NM_033225.6:c.7`
- A: `26CGH132-TwistMyVal	chr11	118491857	118491857	A	G	KMT2A	missense_variant	ENST00000534358.8:c.4933A>G	ENSP00000436786.2:p.Ile1645Val	chr11:g.118491857A>G	NM_0011`
- A: `26CGH132-TwistMyVal	chr5	171410541	171410541	C	CTGCA	NPM1	frameshift_variant	ENST00000296930.10:c.863_864insCATG	ENSP00000296930.5:p.Trp288CysfsTer12	chr5:g.171`
- B: `26CGH132-TwistMyVal	chr20	32435819	32435819	A	G	ASXL1	missense_variant	ENST00000375687.10:c.3107A>G	ENSP00000364839.4:p.Asn1036Ser	chr20:g.32435819A>G	NM_015338`
- B: `26CGH132-TwistMyVal	chr8	2974569	2974569	C	T	CSMD1	synonymous_variant	ENST00000635120.2:c.8622G>A	ENSP00000489225.1:p.Leu2874%3D	chr8:g.2974569C>T	NM_033225.6:c`
- B: `26CGH132-TwistMyVal	chr8	3029439	3029439	C	T	CSMD1	missense_variant	ENST00000635120.2:c.7735G>A	ENSP00000489225.1:p.Glu2579Lys	chr8:g.3029439C>T	NM_033225.6:c.7`
- B: `26CGH132-TwistMyVal	chr11	118491857	118491857	A	G	KMT2A	missense_variant	ENST00000534358.8:c.4933A>G	ENSP00000436786.2:p.Ile1645Val	chr11:g.118491857A>G	NM_0011`
- B: `26CGH132-TwistMyVal	chr5	171410541	171410541	C	CTGCA	NPM1	frameshift_variant	ENST00000296930.10:c.863_864insCATG	ENSP00000296930.5:p.Trp288CysfsTer12	chr5:g.171`

### 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5191, clinical23=5262; only-in-gandalf 10, only-in-clinical23 81

- A: `26CGH132-TwistMyVal	chr10	125426040	125426040	A	C	-1	intergenic_variant	-1	-1	MODIFIER	1	VarDict	1260	66	4.98	REJECT	-1	-1	-1	-1	-1	-1	0.0883	0.1611	rs77300345	`
- A: `26CGH132-TwistMyVal	chr10	38249880	38249880	A	AT	PLD5P1	intron_variant&NMD_transcript_variant	ENST00000640275.1:c.*789+1824dup	-1	MODIFIER	1	VarDict	1026	35	3.3`
- A: `26CGH132-TwistMyVal	chr11	119206522	119206525	GCAC	G	CBL	inframe_deletion	ENST00000264033.6:c.125_127del	ENSP00000264033.3:p.His42del	MODERATE	1	Strelka	1400	40`
- A: `26CGH132-TwistMyVal	chr11	43686570	43686570	G	C	HSD17B12	intron_variant	ENST00000278353.10:c.160+5583G>C	-1	MODIFIER	1	FreeBayes	1162	144	11.0	REJECT	-1	-1	-1	-`
- A: `26CGH132-TwistMyVal	chr17	44207116	44207116	A	T	UBTF	3_prime_UTR_variant	ENST00000436088.6:c.*126T>A	-1	MODIFIER	1	VarDict	1039	29	2.72	REJECT	-1	-1	-1	-1	-1	-1`
- B: `26CGH132-TwistMyVal	chr10	125426040	125426040	A	C	-1	intergenic_variant	-1	-1	MODIFIER	2	VarScan,VarDict	1260	66	4.98	REJECT	-1	-1	-1	-1	-1	-1	0.0883	0.1611	rs7`
- B: `26CGH132-TwistMyVal	chr10	132512630	132512630	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-469C>T	-1	MODIFIER	1	VarScan	1732	46	2`
- B: `26CGH132-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	23`
- B: `26CGH132-TwistMyVal	chr10	38249880	38249880	A	AT	PLD5P1	intron_variant&NMD_transcript_variant	ENST00000640275.1:c.*789+1824dup	-1	MODIFIER	2	VarScan,VarDict	102`
- B: `26CGH132-TwistMyVal	chr10	87965473	87965474	AT	A	PTEN	3_prime_UTR_variant	ENST00000371953.8:c.*10del	-1	MODIFIER	1	VarScan	1152	25	2.12	REJECT	-1	Uncertain_sign`

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

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=18, clinical23=19; only-in-gandalf 16, only-in-clinical23 17

- A: `26CGH1480-TwistMyVal	chr11	102328932	102328932	T	C	BIRC3	synonymous_variant	ENST00000263464.9:c.1068T>C	ENSP00000263464.4:p.Asn356%3D	chr11:g.102328932T>C	NM_00`
- A: `26CGH1480-TwistMyVal	chr7	134662091	134662091	T	A	BPGM	missense_variant	ENST00000344924.8:c.584T>A	ENSP00000342032.3:p.Leu195His	chr7:g.134662091T>A	NM_001724.5`
- A: `26CGH1480-TwistMyVal	chr3	105658984	105658984	G	A	CBLB	missense_variant	ENST00000394030.8:c.2935C>T	ENSP00000377598.4:p.Arg979Cys	chr3:g.105658984G>A	NM_170662.`
- A: `26CGH1480-TwistMyVal	chr7	102248852	102248852	A	ACAG	CUX1	inframe_insertion	ENST00000292535.12:c.4342_4344dup	ENSP00000292535.7:p.Ser1448dup	chr7:g.102248866_10`
- A: `26CGH1480-TwistMyVal	chr2	46360953	46360953	C	T	EPAS1	synonymous_variant	ENST00000263734.5:c.642C>T	ENSP00000263734.3:p.Tyr214%3D	chr2:g.46360953C>T	NM_001430.5`
- B: `26CGH1480-TwistMyVal	chr11	102328932	102328932	T	C	BIRC3	synonymous_variant	ENST00000263464.9:c.1068T>C	ENSP00000263464.4:p.Asn356%3D	chr11:g.102328932T>C	NM_00`
- B: `26CGH1480-TwistMyVal	chr7	134662091	134662091	T	A	BPGM	missense_variant	ENST00000344924.8:c.584T>A	ENSP00000342032.3:p.Leu195His	chr7:g.134662091T>A	NM_001724.5`
- B: `26CGH1480-TwistMyVal	chr11	119206524	119206524	A	C	CBL	missense_variant	ENST00000264033.6:c.107A>C	ENSP00000264033.3:p.His36Pro	chr11:g.119206524A>C	NM_005188.4`
- B: `26CGH1480-TwistMyVal	chr3	105658984	105658984	G	A	CBLB	missense_variant	ENST00000394030.8:c.2935C>T	ENSP00000377598.4:p.Arg979Cys	chr3:g.105658984G>A	NM_170662.`
- B: `26CGH1480-TwistMyVal	chr7	102248852	102248852	A	ACAG	CUX1	inframe_insertion	ENST00000292535.12:c.4342_4344dup	ENSP00000292535.7:p.Ser1448dup	chr7:g.102248866_10`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5374, clinical23=5471; only-in-gandalf 11, only-in-clinical23 108

- A: `26CGH1480-TwistMyVal	chr11	119206524	119206524	A	C	CBL	missense_variant	ENST00000264033.6:c.107A>C	ENSP00000264033.3:p.His36Pro	MODERATE	1	FreeBayes	1215	75	5.8`
- A: `26CGH1480-TwistMyVal	chr11	119206539	119206539	A	C	CBL	missense_variant	ENST00000264033.6:c.122A>C	ENSP00000264033.3:p.His41Pro	MODERATE	1	FreeBayes	1160	135	10`
- A: `26CGH1480-TwistMyVal	chr11	86245103	86245103	T	TG	EED	5_prime_UTR_variant	ENST00000263360.11:c.-119dup	-1	MODIFIER	1	Platypus	820	18	2.15	REJECT	-1	-1	-1	-1	-1	`
- A: `26CGH1480-TwistMyVal	chr12	121831757	121831757	G	C	SETD1B	3_prime_UTR_variant	ENST00000604567.6:c.*1518G>C	-1	MODIFIER	1	FreeBayes	1436	160	10.0	REJECT	-1	-1	-1`
- A: `26CGH1480-TwistMyVal	chr17	44207116	44207116	A	T	UBTF	3_prime_UTR_variant	ENST00000436088.6:c.*126T>A	-1	MODIFIER	2	Mutect2,VarDict	1108	41	3.57	REJECT	-1	-1	-1`
- B: `26CGH1480-TwistMyVal	chr10	119218249	119218249	C	CA	GRK5	intron_variant	ENST00000392870.3:c.52+10281dup	-1	MODIFIER	1	VarScan	1036	28	2.63	REJECT	-1	-1	-1	-1	-1`
- B: `26CGH1480-TwistMyVal	chr10	132512630	132512630	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-469C>T	-1	MODIFIER	1	VarScan	1897	62	`
- B: `26CGH1480-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	1`
- B: `26CGH1480-TwistMyVal	chr10	27877619	27877620	GA	G	ODAD2	intron_variant	ENST00000305242.10:c.2611-14998del	-1	MODIFIER	1	VarScan	960	26	2.64	REJECT	-1	-1	-1	-1	-`
- B: `26CGH1480-TwistMyVal	chr10	50343976	50343977	GT	G	SGMS1	frameshift_variant	ENST00000361781.7:c.138del	ENSP00000354829.2:p.Lys46AsnfsTer18	HIGH	1	VarScan	1206	28`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_genebe_cache.json

lines gandalf=274, clinical23=290; only-in-gandalf 17, only-in-clinical23 27

- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `  "chr11:119206524:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:27 UTC",`
- B: `    "acmg_criteria": "PM2_Supporting",`
- B: `    "acmg_score": 1,`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:14:44 GMT 2026`
- B: `# Started on: Fri Sep 11 02:36:20 GMT 2026`

### 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_mobidetails_cache.json

lines gandalf=2030, clinical23=2036; only-in-gandalf 17, only-in-clinical23 21

- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:29 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr11:119206524:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "hgvs_g": "NC_000011.10:g.119206524A>C",`
- B: `    "warning": "The variant NC_000011.10:g.119206524A>C does not exist yet in MD"`

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

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=6, clinical23=8; only-in-gandalf 5, only-in-clinical23 7

- A: `26CGH60-TwistMyVal	chrX	44873580	44873580	C	T	KDM6A	missense_variant	ENST00000611820.5:c.29C>T	ENSP00000483595.2:p.Thr10Ile	chrX:g.44873580C>T	NM_001291415.2:c.`
- A: `26CGH60-TwistMyVal	chr17	7849191	7849191	T	G	KDM6B	missense_variant	ENST00000448097.7:c.2903T>G	ENSP00000412513.2:p.Val968Gly	chr17:g.7849191T>G	NM_001348716.2:`
- A: `26CGH60-TwistMyVal	chr9	36882052	36882053	CG	C	PAX5	frameshift_variant	ENST00000358127.9:c.963del	ENSP00000350844.4:p.Ala322LeufsTer11	chr9:g.36882059del	NM_016`
- A: `26CGH60-TwistMyVal	chr4	105272673	105272673	G	C	TET2	missense_variant	ENST00000380013.9:c.4292G>C	ENSP00000369351.4:p.Ser1431Thr	chr4:g.105272673G>C	NM_00112720`
- A: `26CGH60-TwistMyVal	chr17	44207341	44207341	G	A	UBTF	synonymous_variant	ENST00000436088.6:c.2196C>T	ENSP00000390669.1:p.Asp732%3D	chr17:g.44207341G>A	NM_014233.4`
- B: `26CGH60-TwistMyVal	chr1	26696451	26696451	G	C	ARID1A	synonymous_variant	ENST00000324856.13:c.48G>C	ENSP00000320485.7:p.Pro16%3D	chr1:g.26696451G>C	NM_006015.6:c`
- B: `26CGH60-TwistMyVal	chrX	44873580	44873580	C	T	KDM6A	missense_variant	ENST00000611820.5:c.29C>T	ENSP00000483595.2:p.Thr10Ile	chrX:g.44873580C>T	NM_001291415.2:c.`
- B: `26CGH60-TwistMyVal	chr17	7849191	7849191	T	G	KDM6B	missense_variant	ENST00000448097.7:c.2903T>G	ENSP00000412513.2:p.Val968Gly	chr17:g.7849191T>G	NM_001348716.2:`
- B: `26CGH60-TwistMyVal	chr22	27797803	27797803	T	C	MN1	missense_variant	ENST00000302326.5:c.2741A>G	ENSP00000304956.4:p.Asp914Gly	chr22:g.27797803T>C	NM_002430.3:c.`
- B: `26CGH60-TwistMyVal	chr9	36882052	36882053	CG	C	PAX5	frameshift_variant	ENST00000358127.9:c.963del	ENSP00000350844.4:p.Ala322LeufsTer11	chr9:g.36882059del	NM_016`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5238, clinical23=5361; only-in-gandalf 18, only-in-clinical23 141

- A: `26CGH60-TwistMyVal	chr10	132512541	132512541	A	AC	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-381dup	-1	MODIFIER	2	Strelka,Platypus	`
- A: `26CGH60-TwistMyVal	chr11	86245103	86245103	T	TG	EED	5_prime_UTR_variant	ENST00000263360.11:c.-119dup	-1	MODIFIER	1	Platypus	891	24	2.62	REJECT	-1	-1	-1	-1	-1	-1`
- A: `26CGH60-TwistMyVal	chr14	99175588	99175588	G	C	BCL11B	synonymous_variant	ENST00000357195.8:c.1248C>G	ENSP00000349723.3:p.Gly416%3D	LOW	1	FreeBayes	1817	136	6.96`
- A: `26CGH60-TwistMyVal	chr17	31374652	31374653	CT	C	NF1	3_prime_UTR_variant	ENST00000358273.9:c.*506del	-1	MODIFIER	1	VarDict	1872	62	3.21	REJECT	-1	-1	-1	-1	-1	-1	`
- A: `26CGH60-TwistMyVal	chr17	44205573	44205573	T	G	UBTF	3_prime_UTR_variant	ENST00000436088.6:c.*1669A>C	-1	MODIFIER	1	FreeBayes	1575	178	10.2	REJECT	-1	-1	-1	-1	-1`
- B: `26CGH60-TwistMyVal	chr10	110577501	110577502	CT	C	SMC3	intron_variant	ENST00000361804.5:c.270+18del	-1	MODIFIER	1	VarScan	1145	27	2.3	REJECT	-1	-1	-1	-1	-1	-1	-`
- B: `26CGH60-TwistMyVal	chr10	131493131	131493132	GA	G	-1	intergenic_variant	-1	-1	MODIFIER	1	VarScan	1602	41	2.5	REJECT	-1	-1	-1	-1	-1	-1	-1	0.6994	rs11336554	-1	-1`
- B: `26CGH60-TwistMyVal	chr10	132512541	132512541	A	AC	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-381dup	-1	MODIFIER	3	VarScan,Strelka,P`
- B: `26CGH60-TwistMyVal	chr10	132512576	132512576	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-415C>T	-1	MODIFIER	1	VarScan	2769	24	0.`
- B: `26CGH60-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	247`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_genebe_cache.json

lines gandalf=82, clinical23=114; only-in-gandalf 5, only-in-clinical23 19

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr1:26696451:G:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "acmg_classification": "Likely_benign",`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 15:49:34 GMT 2026`
- B: `# Started on: Fri Sep 11 02:37:30 GMT 2026`

### 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_mobidetails_cache.json

lines gandalf=242, clinical23=470; only-in-gandalf 5, only-in-clinical23 84

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr1:26696451:G:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `        "chr": "1",`

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

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=8, clinical23=9; only-in-gandalf 7, only-in-clinical23 8

- A: `26CGH799-TwistMyVal	chr11	108271098	108271098	A	G	ATM	missense_variant	ENST00000675843.1:c.2873A>G	ENSP00000501606.1:p.Glu958Gly	chr11:g.108271098A>G	NM_000051.`
- A: `26CGH799-TwistMyVal	chr6	99550251	99550251	A	G	CCNC	missense_variant	ENST00000520429.6:c.497T>C	ENSP00000428982.1:p.Met166Thr	chr6:g.99550251A>G	NM_005190.4:c.4`
- A: `26CGH799-TwistMyVal	chr5	150060893	150060893	G	A	CSF1R	synonymous_variant	ENST00000675795.1:c.1938C>T	ENSP00000501699.1:p.Ile646%3D	chr5:g.150060893G>A	NM_00128`
- A: `26CGH799-TwistMyVal	chr13	28034083	28034083	A	AAACTCTAAATTTTCTCTTGGAAACTCCCATTTGAGATCATATTCATAT	FLT3	inframe_insertion&splice_region_variant	ENST00000241453.12:`
- A: `26CGH799-TwistMyVal	chr22	27799767	27799767	A	G	MN1	synonymous_variant	ENST00000302326.5:c.777T>C	ENSP00000304956.4:p.Tyr259%3D	chr22:g.27799767A>G	NM_002430.3:`
- B: `26CGH799-TwistMyVal	chr1	26696451	26696451	G	C	ARID1A	synonymous_variant	ENST00000324856.13:c.48G>C	ENSP00000320485.7:p.Pro16%3D	chr1:g.26696451G>C	NM_006015.6:`
- B: `26CGH799-TwistMyVal	chr11	108271098	108271098	A	G	ATM	missense_variant	ENST00000675843.1:c.2873A>G	ENSP00000501606.1:p.Glu958Gly	chr11:g.108271098A>G	NM_000051.`
- B: `26CGH799-TwistMyVal	chr6	99550251	99550251	A	G	CCNC	missense_variant	ENST00000520429.6:c.497T>C	ENSP00000428982.1:p.Met166Thr	chr6:g.99550251A>G	NM_005190.4:c.4`
- B: `26CGH799-TwistMyVal	chr5	150060893	150060893	G	A	CSF1R	synonymous_variant	ENST00000675795.1:c.1938C>T	ENSP00000501699.1:p.Ile646%3D	chr5:g.150060893G>A	NM_00128`
- B: `26CGH799-TwistMyVal	chr13	28034083	28034083	A	AAACTCTAAATTTTCTCTTGGAAACTCCCATTTGAGATCATATTCATAT	FLT3	inframe_insertion&splice_region_variant	ENST00000241453.12:`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5374, clinical23=5483; only-in-gandalf 11, only-in-clinical23 120

- A: `26CGH799-TwistMyVal	chr14	99172951	99172951	A	C	BCL11B	3_prime_UTR_variant	ENST00000357195.8:c.*1200T>G	-1	MODIFIER	1	FreeBayes	921	99	9.71	REJECT	-1	-1	-1	-1	-`
- A: `26CGH799-TwistMyVal	chr14	99175588	99175588	G	T	BCL11B	synonymous_variant	ENST00000357195.8:c.1248C>A	ENSP00000349723.3:p.Gly416%3D	LOW	1	FreeBayes	1553	93	5.65`
- A: `26CGH799-TwistMyVal	chr17	30646771	30646771	G	GT	-1	intron_variant&non_coding_transcript_variant	ENST00000578265.5:n.288-1596_288-1595insT	-1	MODIFIER	1	Mutect2`
- A: `26CGH799-TwistMyVal	chr17	42314479	42314479	C	G	STAT3	3_prime_UTR_variant	ENST00000264657.10:c.*1266G>C	-1	MODIFIER	1	FreeBayes	1058	119	10.1	REJECT	-1	-1	-1	-1`
- A: `26CGH799-TwistMyVal	chr19	4044974	4044974	T	G	ZBTB7A	3_prime_UTR_variant	ENST00000322357.9:c.*2778A>C	-1	MODIFIER	1	FreeBayes	691	67	8.84	REJECT	-1	-1	-1	-1	-1	`
- B: `26CGH799-TwistMyVal	chr10	110577501	110577502	CT	C	SMC3	intron_variant	ENST00000361804.5:c.270+18del	-1	MODIFIER	1	VarScan	872	24	2.68	REJECT	-1	-1	-1	-1	-1	-1	`
- B: `26CGH799-TwistMyVal	chr10	132512538	132512538	A	G	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-377T>C	-1	MODIFIER	1	VarScan	959	25	2.`
- B: `26CGH799-TwistMyVal	chr10	132512630	132512630	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-469C>T	-1	MODIFIER	1	VarScan	1944	52	2`
- B: `26CGH799-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	19`
- B: `26CGH799-TwistMyVal	chr10	87863921	87863924	CGCG	C	PTEN	5_prime_UTR_variant	ENST00000371953.8:c.-534_-532del	-1	MODIFIER	1	VarScan	1212	35	2.81	REJECT	-1	-1	-1	`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_genebe_cache.json

lines gandalf=114, clinical23=130; only-in-gandalf 7, only-in-clinical23 13

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr1:26696451:G:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 14:49:25 GMT 2026`
- B: `# Started on: Fri Sep 11 02:33:58 GMT 2026`

### 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_mobidetails_cache.json

lines gandalf=686, clinical23=908; only-in-gandalf 7, only-in-clinical23 69

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr1:26696451:G:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`

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

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal.somaticseq.clinical.final.tsv

lines gandalf=10, clinical23=12; only-in-gandalf 8, only-in-clinical23 10

- A: `26CGH885-TwistMyVal	chr11	108304736	108304736	A	T	ATM	missense_variant	ENST00000675843.1:c.5558A>T	ENSP00000501606.1:p.Asp1853Val	chr11:g.108304736A>T	NM_000051`
- A: `26CGH885-TwistMyVal	chr19	33301878	33301878	G	GA	CEBPA	frameshift_variant	ENST00000498907.3:c.536dup	ENSP00000427514.1:p.Tyr181LeufsTer140	chr19:g.33301880dup	N`
- A: `26CGH885-TwistMyVal	chr2	25243898	25243898	C	G	DNMT3A	missense_variant&splice_region_variant	ENST00000321117.10:c.1936G>C	ENSP00000324375.5:p.Gly646Arg	chr2:g.2`
- A: `26CGH885-TwistMyVal	chr3	128486004	128486004	C	A	GATA2	synonymous_variant	ENST00000341105.7:c.594G>T	ENSP00000345681.2:p.Ala198%3D	chr3:g.128486004C>A	NM_032638`
- A: `26CGH885-TwistMyVal	chr1	1806503	1806503	A	T	GNB1	missense_variant	ENST00000378609.9:c.239T>A	ENSP00000367872.3:p.Ile80Asn	chr1:g.1806503A>T	NM_002074.5:c.239T>`
- B: `26CGH885-TwistMyVal	chr11	108304736	108304736	A	T	ATM	missense_variant	ENST00000675843.1:c.5558A>T	ENSP00000501606.1:p.Asp1853Val	chr11:g.108304736A>T	NM_000051`
- B: `26CGH885-TwistMyVal	chr11	119206533	119206533	A	C	CBL	missense_variant	ENST00000264033.6:c.116A>C	ENSP00000264033.3:p.His39Pro	chr11:g.119206533A>C	NM_005188.4:`
- B: `26CGH885-TwistMyVal	chr11	119206536	119206536	A	C	CBL	missense_variant	ENST00000264033.6:c.119A>C	ENSP00000264033.3:p.His40Pro	chr11:g.119206536A>C	NM_005188.4:`
- B: `26CGH885-TwistMyVal	chr19	33301878	33301878	G	GA	CEBPA	frameshift_variant	ENST00000498907.3:c.536dup	ENSP00000427514.1:p.Tyr181LeufsTer140	chr19:g.33301880dup	N`
- B: `26CGH885-TwistMyVal	chr2	25243898	25243898	C	G	DNMT3A	missense_variant&splice_region_variant	ENST00000321117.10:c.1936G>C	ENSP00000324375.5:p.Gly646Arg	chr2:g.2`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal.somaticseq.filtered.tsv

lines gandalf=5327, clinical23=5412; only-in-gandalf 11, only-in-clinical23 96

- A: `26CGH885-TwistMyVal	chr10	132512541	132512541	A	AC	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-381dup	-1	MODIFIER	1	Strelka	1005	23	`
- A: `26CGH885-TwistMyVal	chr11	119206533	119206533	A	C	CBL	missense_variant	ENST00000264033.6:c.116A>C	ENSP00000264033.3:p.His39Pro	MODERATE	1	FreeBayes	1303	108	7.6`
- A: `26CGH885-TwistMyVal	chr11	119206536	119206536	A	C	CBL	missense_variant	ENST00000264033.6:c.119A>C	ENSP00000264033.3:p.His40Pro	MODERATE	1	FreeBayes	1297	105	7.4`
- A: `26CGH885-TwistMyVal	chr11	119206539	119206539	A	C	CBL	missense_variant	ENST00000264033.6:c.122A>C	ENSP00000264033.3:p.His41Pro	MODERATE	1	FreeBayes	1255	163	11.`
- A: `26CGH885-TwistMyVal	chr17	44207116	44207116	A	T	UBTF	3_prime_UTR_variant	ENST00000436088.6:c.*126T>A	-1	MODIFIER	1	Mutect2	1171	30	2.5	REJECT	-1	-1	-1	-1	-1	-1	`
- B: `26CGH885-TwistMyVal	chr10	132512541	132512541	A	AC	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-381dup	-1	MODIFIER	2	VarScan,Strelka	`
- B: `26CGH885-TwistMyVal	chr10	132512630	132512630	G	A	-1	intron_variant&non_coding_transcript_variant	ENST00000660050.1:n.252-469C>T	-1	MODIFIER	1	VarScan	2087	66	3`
- B: `26CGH885-TwistMyVal	chr10	27048876	27048879	CCAT	C	ANKRD26	inframe_deletion	ENST00000376087.5:c.1736_1738del	ENSP00000365255.4:p.Asp579del	MODERATE	1	VarScan	20`
- B: `26CGH885-TwistMyVal	chr10	87863921	87863924	CGCG	C	PTEN	5_prime_UTR_variant	ENST00000371953.8:c.-534_-532del	-1	MODIFIER	1	VarScan	1304	34	2.54	REJECT	-1	-1	-1	`
- B: `26CGH885-TwistMyVal	chr10	87965473	87965474	AT	A	PTEN	3_prime_UTR_variant	ENST00000371953.8:c.*10del	-1	MODIFIER	1	VarScan	1215	42	3.34	REJECT	-1	Uncertain_sign`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_genebe_cache.json

lines gandalf=146, clinical23=178; only-in-gandalf 9, only-in-clinical23 22

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr11:119206533:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "acmg_criteria": "PM2",`
- B: `    "acmg_score": 2,`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_hsmetrics.txt

lines gandalf=213, clinical23=213; only-in-gandalf 1, only-in-clinical23 1

- A: `# Started on: Thu Sep 10 14:38:29 GMT 2026`
- B: `# Started on: Fri Sep 11 02:40:40 GMT 2026`

### 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_mobidetails_cache.json

lines gandalf=1563, clinical23=1575; only-in-gandalf 9, only-in-clinical23 17

- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- A: `    "_fetched_at": "2026-09-10 16:30 UTC",`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `  "chr11:119206533:A:C": {`
- B: `    "_fetched_at": "2026-09-11 05:28 UTC",`
- B: `    "hgvs_g": "NC_000011.10:g.119206533A>C",`
- B: `    "warning": "The variant NC_000011.10:g.119206533A>C does not exist yet in MD"`

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

## Cosmetic-only differences (10)

- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1043-TwistMyVal_R1.fastq.gz -I 26CGH1043-TwistMyVal_R2.fastq.gz -o 26CGH1043-TwistMyVal_trim_R1.fastq.gz -O 26CGH1043-TwistMyVal_trim`)
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1250-TwistMyVal_R1.fastq.gz -I 26CGH1250-TwistMyVal_R2.fastq.gz -o 26CGH1250-TwistMyVal_trim_R1.fastq.gz -O 26CGH1250-TwistMyVal_trim`)
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1292-TwistMyVal_R1.fastq.gz -I 26CGH1292-TwistMyVal_R2.fastq.gz -o 26CGH1292-TwistMyVal_trim_R1.fastq.gz -O 26CGH1292-TwistMyVal_trim`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH132-TwistMyVal_R1.fastq.gz -I 26CGH132-TwistMyVal_R2.fastq.gz -o 26CGH132-TwistMyVal_trim_R1.fastq.gz -O 26CGH132-TwistMyVal_trim_R2.`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_genebe_cache.json (only-in-gandalf 10, only-in-clinical23 10; e.g. `    "_fetched_at": "2026-09-10 16:29 UTC",`)
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_mobidetails_cache.json (only-in-gandalf 10, only-in-clinical23 10; e.g. `    "_fetched_at": "2026-09-10 16:29 UTC",`)
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH1480-TwistMyVal_R1.fastq.gz -I 26CGH1480-TwistMyVal_R2.fastq.gz -o 26CGH1480-TwistMyVal_trim_R1.fastq.gz -O 26CGH1480-TwistMyVal_trim`)
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH60-TwistMyVal_R1.fastq.gz -I 26CGH60-TwistMyVal_R2.fastq.gz -o 26CGH60-TwistMyVal_trim_R1.fastq.gz -O 26CGH60-TwistMyVal_trim_R2.fast`)
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH799-TwistMyVal_R1.fastq.gz -I 26CGH799-TwistMyVal_R2.fastq.gz -o 26CGH799-TwistMyVal_trim_R1.fastq.gz -O 26CGH799-TwistMyVal_trim_R2.`)
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_fastp.json (only-in-gandalf 1, only-in-clinical23 1; e.g. `	"command": "fastp -i 26CGH885-TwistMyVal_R1.fastq.gz -I 26CGH885-TwistMyVal_R2.fastq.gz -o 26CGH885-TwistMyVal_trim_R1.fastq.gz -O 26CGH885-TwistMyVal_trim_R2.`)

## Binary / other files that differ by md5 (109)

- 26CGH1043-TwistMyVal/26CGH1043-TwistMyVal_report.zip
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.final.bam
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal.final.bam.bai
- 26CGH1043-TwistMyVal/clinical/26CGH1043-TwistMyVal_dashboard.html
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
- 26CGH1250-TwistMyVal/clinical/26CGH1250-TwistMyVal_dashboard.html
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
- 26CGH1292-TwistMyVal/clinical/26CGH1292-TwistMyVal_dashboard.html
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
- 26CGH132-TwistMyVal/clinical/26CGH132-TwistMyVal_dashboard.html
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
- 26CGH1480-TwistMyVal/clinical/26CGH1480-TwistMyVal_dashboard.html
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
- 26CGH60-TwistMyVal/clinical/26CGH60-TwistMyVal_dashboard.html
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
- 26CGH799-TwistMyVal/clinical/26CGH799-TwistMyVal_dashboard.html
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
- 26CGH885-TwistMyVal/clinical/26CGH885-TwistMyVal_dashboard.html
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

