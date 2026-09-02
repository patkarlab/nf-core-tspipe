# DECoN working copies (exon-level CNV arm, evaluation 2026-09-02)

Source: RahmanTeam/DECoN master, Linux/ scripts (MIT). Two edits:
1. `renv::restore()` removed from line 1 of each script; run with
   `Rscript --vanilla` in conda env `decon` (r-base 4.3, r-exomedepth
   1.1.16, r-optparse, r-r.utils, r-ggplot2, r-reshape).
2. Sample columns located by name (`grep("\\.bam$", ...)`) instead of
   position: ExomeDepth 1.1.16 inserts a GC column when --fasta is given,
   which shifts DECoN's positional labels by one.

Inputs: BAM list; twist_myeloid_exons.bed (1,778 merged targets, 126
genes, col4 = gene symbol, genomic order); reference fasta.
Do not use --exons/--custom with IdentifyFailures (crashes); map
Start.b/End.b to exon names from twist_myeloid_exon_numbering.tsv.

    Rscript --vanilla ReadInBams.R --bams bams.txt --bed twist_myeloid_exons.bed --fasta <ref> --out pool
    Rscript --vanilla IdentifyFailures.R --RData pool.RData --mincorr .98 --mincov 100 --out pool
    Rscript --vanilla makeCNVcalls.R --RData pool.RData --transProb 0.01 --out poolcalls --plot All --plotFolder plots
