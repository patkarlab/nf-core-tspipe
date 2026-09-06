# EXON_PLOTS_V1 -- per-sample exon-level copy-ratio figures as a module -- 2026-09-06

Replaces the ad hoc plotting loop. One PNG per chromosome that carries a
non-neutral consensus gene, a DECoN call at BF >= params.exon_plot_min_bf
(5; sub-threshold calls on purpose), or a focal-CNV gene
(assets/<panel>/targets.focal_cnv.bed when present); all panel genes of the
chromosome on the axis in genomic order; DECoN calls as brackets with BF,
ratio and decision; index TSV for the dashboard.

Files
    bin/plot_exon_ratio.py          renderer (importable render() + CLI); moved from tools/
    bin/plot_exon_ratio_batch.py    selection + index; called by the module
    modules/local/exon_plots.nf     EXON_PLOTS (GATK container: Python 3.6 + matplotlib 3.2)
    tools/patches/2026-09-06/patch_exon_plots_v1.py   twist_apply.config + tspipe.nf

Placement (repo root)
    git mv tools/plot_exon_ratio.py bin/plot_exon_ratio.py
    cp <bundle>/bin/plot_exon_ratio.py <bundle>/bin/plot_exon_ratio_batch.py bin/
    cp <bundle>/modules/local/exon_plots.nf modules/local/
    cp <bundle>/tools/patches/2026-09-06/patch_exon_plots_v1.py tools/patches/2026-09-06/
    chmod +x bin/plot_exon_ratio.py bin/plot_exon_ratio_batch.py
    python3 tools/patches/2026-09-06/patch_exon_plots_v1.py [--apply]

Wiring: after CNV_CONSENSUS_MULTI in the twist block; input join of the
consensus JSON, the consensus genes TSV and DECON.out.filtered (an empty
placeholder when DECoN is off, so the process still runs without brackets).
Published to <outdir>/<sample>/cnv_consensus_multi/exon_plots/ (sample level,
outside the sweep list; moves under clinical/ with the item 12 ORGANIZE_OUTPUT
routing, when the dashboard also starts reading the index).

A run launched before this patch is extended by resuming it with its session
uuid; the consensus is cached, EXON_PLOTS runs for every sample in minutes.
