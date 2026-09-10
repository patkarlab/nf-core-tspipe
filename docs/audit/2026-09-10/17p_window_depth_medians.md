# 17p SNP-window depth ratio — eight run8 samples, 2026-09-10 (ARM17P_V2 pre-flight)

`plot_arm_17p.py` `[medians]` lines, full allelic counts, background = 48 normals. "raw" = median
over 17p windows of log2(sample / cohort median depth); "backbone ref" = the same ratio's median
over all catalog positions outside chr17 (4,199); "normalised" = raw − backbone ref.

| sample | exon-bin arm median | 17p windows raw | backbone ref | normalised | BAF_V2 17p | PURPLE at TP53 |
|---|---|---|---|---|---|---|
| 26CGH1043 | −0.013 | −0.120 | +0.010 | −0.131 | NEUTRAL f 0.053 | 2.00 / 1.00 |
| 26CGH1250 | **+0.310** | −0.006 | −0.140 | **+0.134** | GAIN f 0.256 HIGH | 3.15 / 1.05 |
| 26CGH1292 | +0.036 | −0.200 | −0.040 | −0.160 | NEUTRAL f 0.056 | 2.24 / 1.00 |
| 26CGH132 | +0.022 | −0.284 | −0.072 | −0.212 | NEUTRAL f 0.067 | 2.04 / 0.93 |
| 26CGH1480 | −0.023 | −0.328 | −0.150 | −0.179 | NEUTRAL f 0.062 | 2.04 / 1.00 |
| 26CGH60 | +0.011 | −0.047 | +0.153 | −0.200 | NEUTRAL f 0.068 | 2.06 / 1.00 |
| 26CGH799 | +0.032 | −0.328 | −0.112 | −0.216 | NEUTRAL f 0.052 | 1.97 / 0.98 |
| 26CGH885 | −0.009 | −0.282 | −0.110 | −0.172 | NEUTRAL f 0.064 | 2.03 / 1.00 |

Reading: raw values track the library's depth relative to the cohort, not copy number. Normalised
values put the seven neutral samples at −0.18 ± 0.03 and the chromosome-17 gain of 26CGH1250 at
+0.31 above that level, matching the exon-bin arm median. The −0.18 is a run-level probe-batch
offset of the 17p supplementary windows relative to the backbone; it needs a per-run calibration
or matched control windows outside 17p (Twist letter).
