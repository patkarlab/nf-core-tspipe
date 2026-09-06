#!/usr/bin/env Rscript
# bin/decon_call_sample.R  (DECON_V1)
#
# One test sample against a precomputed DECoN pool. The pool is the RData
# written by ReadInBams.R over the stratum normals (counts, bams, bed.file,
# sample.names, fasta); the sample RData is ReadInBams.R over the test BAM
# alone. This script replicates makeCNVcalls.R for a single test sample
# (reference selection + CallCNVs, DECoN's call formatting incl. multi-gene
# splitting) and IdentifyFailures.R's whole-sample checks for that sample.
# No plots. Output columns of <out>_all.txt match DECoN's *calls_all.txt so
# filter_decon_calls.py runs unchanged.
#
# Run with the conda env 'decon' (r-base 4.3, ExomeDepth 1.1.16):
#   Rscript --vanilla decon_call_sample.R --pool pool.RData --sample S.RData \
#       --id S --out S.decon

suppressPackageStartupMessages({
    library(optparse)
    library(ExomeDepth)
})

option_list <- list(
    make_option("--pool",      dest = "pool",      default = NULL, help = "pool RData (ReadInBams.R over the stratum normals)"),
    make_option("--sample",    dest = "sample",    default = NULL, help = "sample RData (ReadInBams.R over the test BAM)"),
    make_option("--id",        dest = "id",        default = NULL, help = "sample id used in outputs"),
    make_option("--transProb", dest = "transProb", default = 0.01, type = "double", help = "HMM transition probability [0.01]"),
    make_option("--mincorr",   dest = "mincorr",   default = 0.98, type = "double", help = "QC: minimum max-correlation with the pool [0.98]"),
    make_option("--mincov",    dest = "mincov",    default = 100,  type = "double", help = "QC: minimum median read count per target [100]"),
    make_option("--out",       dest = "out",       default = "decon", help = "output prefix")
)
opt <- parse_args(OptionParser(option_list = option_list))
if (is.null(opt$pool) || is.null(opt$sample) || is.null(opt$id)) {
    stop("--pool, --sample and --id are required")
}

load_env <- function(path) {
    e <- new.env()
    load(path, envir = e)
    for (v in c("counts", "bed.file", "sample.names")) {
        if (!exists(v, envir = e)) stop(paste0(path, ": missing object ", v))
    }
    e
}

pool <- load_env(opt$pool)
smp  <- load_env(opt$sample)

P <- as(pool$counts, "data.frame")
S <- as(smp$counts, "data.frame")

# Sample columns end in .bam (DECoN edit 2: locate by name, ExomeDepth 1.1.16
# inserts a GC column when --fasta is given).
sc_p <- grep("\\.bam$", colnames(P))
if (length(sc_p) != length(pool$sample.names)) stop("pool: sample columns do not match sample.names")
colnames(P)[sc_p] <- pool$sample.names
sc_s <- grep("\\.bam$", colnames(S))
if (length(sc_s) != 1) stop("sample RData must hold exactly one BAM column")
test_name <- smp$sample.names[1]
colnames(S)[sc_s] <- test_name

if (nrow(P) != nrow(S) || any(P$start != S$start) || any(P$end != S$end) ||
    any(as.character(P$chromosome) != as.character(S$chromosome))) {
    stop("pool and sample were counted over different targets (BED mismatch)")
}

bed <- pool$bed.file
chrom <- gsub("chr", "", as.character(P$chromosome))
exon_name <- if ("exon" %in% colnames(P)) P$exon else if ("name" %in% colnames(P)) P$name else as.character(bed[, 4])
gene_of_row <- as.character(bed[, 4])
# exon index within gene, robust to non-contiguous gene blocks
gene_index <- ave(seq_along(gene_of_row), gene_of_row, FUN = seq_along)

my.test    <- as.numeric(S[[test_name]])
ref_matrix <- as.matrix(P[, pool$sample.names, drop = FALSE])

# ---- QC gate (IdentifyFailures.R whole-sample checks for the test sample)
corr_all   <- apply(ref_matrix, 2, function(r) suppressWarnings(cor(my.test, r)))
max_corr   <- max(corr_all, na.rm = TRUE)
med_depth  <- median(my.test)
corr_pass  <- is.finite(max_corr) && max_corr >= opt$mincorr
depth_pass <- med_depth >= opt$mincov
qc_pass    <- corr_pass && depth_pass

# ---- reference selection + calling (makeCNVcalls.R, single test sample)
choice <- select.reference.set(test.counts = my.test, reference.counts = ref_matrix,
                               bin.length = (P$end - P$start) / 1000, n.bins.reduced = 10000)
sel <- choice$reference.choice
my.matrix    <- ref_matrix[, sel, drop = FALSE]
my.reference <- apply(my.matrix, MARGIN = 1, FUN = sum)
all.exons <- new("ExomeDepth", test = my.test, reference = my.reference,
                 formula = "cbind(test, reference) ~ 1")
all.exons <- CallCNVs(x = all.exons, transition.probability = opt$transProb,
                      chromosome = chrom, start = P$start, end = P$end, name = exon_name)
corr_sel <- suppressWarnings(cor(my.test, my.reference))
calls <- all.exons@CNV.calls

# ---- format as DECoN *calls_all.txt (one row per gene; multi-gene calls split)
out_cols <- c("CNV.ID", "Sample", "Correlation", "N.comp", "Start.b", "End.b",
              "CNV.type", "N.exons", "Start", "End", "Chromosome", "Genomic.ID",
              "BF", "Reads.expected", "Reads.observed", "Reads.ratio", "Gene",
              "N.exons.gene")
rows <- list()
if (!is.null(calls) && nrow(calls) > 0) {
    for (i in seq_len(nrow(calls))) {
        cl <- calls[i, ]
        span <- cl$start.p:cl$end.p
        genes <- unique(gene_of_row[span])
        for (g in genes) {
            ov <- intersect(which(gene_of_row == g), span)
            rows[[length(rows) + 1]] <- data.frame(
                CNV.ID = i, Sample = test_name, Correlation = corr_sel, N.comp = length(sel),
                Start.b = gene_index[min(ov)], End.b = gene_index[max(ov)],
                CNV.type = as.character(cl$type), N.exons = cl$nexons,
                Start = cl$start, End = cl$end, Chromosome = as.character(cl$chromosome),
                Genomic.ID = as.character(cl$id), BF = cl$BF,
                Reads.expected = cl$reads.expected, Reads.observed = cl$reads.observed,
                Reads.ratio = cl$reads.ratio, Gene = g, N.exons.gene = length(ov),
                stringsAsFactors = FALSE)
        }
    }
}
calls_out <- if (length(rows)) do.call(rbind, rows) else
    as.data.frame(setNames(replicate(length(out_cols), character(0), simplify = FALSE), out_cols))
write.table(calls_out[, out_cols], file = paste0(opt$out, "_all.txt"), sep = "\t",
            quote = FALSE, row.names = FALSE, col.names = TRUE)

# ---- QC table (one row)
qc <- data.frame(
    sample = opt$id, test_name = test_name, pool = basename(opt$pool),
    pool_n = length(pool$sample.names), max_corr = round(max_corr, 4),
    median_depth = med_depth, corr_pass = corr_pass, depth_pass = depth_pass,
    qc_pass = qc_pass, n_ref_selected = length(sel), corr_selected_ref = round(corr_sel, 4),
    n_calls = nrow(calls_out), mincorr = opt$mincorr, mincov = opt$mincov,
    transProb = opt$transProb, stringsAsFactors = FALSE)
write.table(qc, file = paste0(opt$out, "_qc.tsv"), sep = "\t", quote = FALSE, row.names = FALSE)

save(all.exons, sel, corr_all, qc, test_name, file = paste0(opt$out, ".RData"))

cat(sprintf("[decon] %s: pool=%s n=%d max_corr=%.4f median_depth=%.0f qc_pass=%s refs=%d calls=%d\n",
            opt$id, basename(opt$pool), length(pool$sample.names), max_corr, med_depth,
            qc_pass, length(sel), nrow(calls_out)))
