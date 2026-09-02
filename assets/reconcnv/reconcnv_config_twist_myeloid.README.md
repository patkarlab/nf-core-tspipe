# reconCNV config for twist_myeloid -- deviations from the template (reconCNV master config.json)

- `files.gene_file.amp_threshold`: 1.5 -> 1.0
- `files.gene_file.loss_threshold`: -0.4 -> -0.5
- `files.genome_build`: 'hg19' -> 'hg38'
- `files.ratio_file.off_target_low_conf_log2`: -10 -> -3.0
- `files.ratio_file.weight_scaling_factor`: 10 -> 3.5
- `plots.bokeh_js_css_code`: 'CDN' -> 'INLINE'
- `plots.chromosome_boundaries.text_angle`: None -> 90
- `plots.chromosome_boundaries.text_strip_chr`: None -> True
- `plots.logFC_genome_plot.point_line_color`: 'black' -> '#b0b6bc'
- `plots.logFC_genome_plot.point_on_target_color`: 'red' -> '#4b5b6b'
- `plots.logFC_ind_plot.point_line_color`: 'black' -> '#b0b6bc'
- `plots.logFC_ind_plot.point_on_target_color`: 'red' -> '#4b5b6b'
- `plots.vaf_plot.height`: 150 -> 250
- `plots.vaf_plot.point_line_color`: 'black' -> '#b0b6bc'
- `plots.vaf_plot.point_size`: 4 -> 3

Everything else is the template default. Requires the reconCNV_portability.patch for
`text_angle` / `text_strip_chr` (label rotation) and for running on pandas >= 2 / Bokeh 2.
Inputs are produced by prep_reconcnv_inputs.py; the gene file is `cnvkit.py genemetrics -t 0 -m 1` (no -s).
