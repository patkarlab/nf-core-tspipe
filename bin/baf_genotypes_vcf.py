#!/usr/bin/env python3
"""baf_genotypes_vcf.py -- catalog-site genotype VCF for SHAPEIT5 + MoChA (MOCHA_17P, step 3).

Reads the GATK CollectAllelicCounts table of one sample and writes, for one contig, a
single-sample VCF at the BAF catalog sites (assets/twist_myeloid/snp_sites.baf.bed) with
FORMAT GT:AD:DP:RAD.

Site positions: catalog rows that are 1-bp intervals (het_<contig>_<pos>_<REF><ALT>, the
backbone convention) are sites as such. Catalog rows that are windows (the 120-bp
Twist17p_rs<id> targets on 17p) contain one or more SNPs; the positions used are, when an
--alleles table is given, every table position inside the window (with a table extracted from
the phasing reference panel this is every 1000G SNP the window covers), otherwise every
"informative" row of baf_background.tsv inside the window (the site definition BAF_V2 uses),
falling back to the window centre (start + 61, 1-based, the design convention). The sites
table records the origin (pos_source = catalog / table / background / window_centre).
With --require-alleles every site absent from the table is dropped (NOT_IN_TABLE): SHAPEIT5
cannot phase a site the reference panel lacks, so such sites are useless to MoChA.

Reference bias, sample-level fallback: sites without a usable cohort term are corrected with
the sample's own global bias estimate (--global-bias auto, the default): the median raw alt
fraction of het-like backbone sites (raw AF 0.2-0.8, depth >= 50) on the other autosomes.
Allelic imbalances split het sites symmetrically around the biased centre, so the median is
robust to copy-number changes; the estimate is written to the VCF header and the summary.
The sites table records which term was applied (bias_source = cohort / global / none).

FORMAT fields:

    GT   unphased genotype called from the alt-allele fraction
         (<= --hom-ref-max -> 0/0, >= --hom-alt-min -> 1/1, otherwise 0/1)
    AD   ref,alt read counts after cohort reference-bias correction (Number=R, as MoChA needs)
    DP   AD sum (equal to the raw depth)
    RAD  raw ref,alt read counts before correction (Number=R)

Reference-bias correction: at a site whose cohort median alt fraction m (baf_background.tsv,
column median_alt_fraction) is het-like -- inside --bias-band, MAD <= --bias-max-mad and at
least --bias-min-het het-like normals -- the counts are rescaled by 0.5/(1-m) (ref) and 0.5/m
(alt) and renormalised to the raw depth, so a diploid sample centres at 0.5. Elsewhere the
counts are written unchanged. MoChA does not model capture reference bias itself (README).

REF and ALT are resolved per site in this order: (1) the catalog name when it embeds them
(het_<contig>_<pos>_<REF><ALT>, the backbone convention); (2) the optional --alleles table
(contig, pos, ref, alt -- normally extracted from the phasing reference panel, so the alleles
match what SHAPEIT5 will see); (3) the counts table itself (REF_NUCLEOTIDE, and ALT_NUCLEOTIDE
only when the site is not hom-ref). The 17p target sites (Twist17p_rs<id>) carry no alleles in
their names, so without --alleles their hom-ref sites cannot be given an ALT and are dropped
as ALT_UNKNOWN; het and hom-alt sites are still written. REF is always checked against the
counts table. Sites are dropped (with a status in the sites table) when they are absent from
the counts, below --min-depth, carry a different REF, or carry a different ALT base above
--hom-ref-max (a different variant at the site). A different ALT base at or below
--hom-ref-max is treated as hom-ref for the catalog allele.

Outputs: the VCF (plain text; the module bgzips and indexes it), a per-site table with every
catalog site of the contig and its status, and an optional key=value summary.

Python 3.6+, standard library only.
"""

import argparse
import re
import sys

VERSION = "baf_genotypes_vcf 1.3 (2026-09-09)"

CATALOG_NAME_RE = re.compile(r"^het_(\S+?)_(\d+)_([ACGT])([ACGT])$")

SITE_COLUMNS = [
    "contig", "pos", "id", "ref", "alt", "pos_source", "allele_source", "status",
    "raw_ref", "raw_alt", "depth", "raw_af",
    "cohort_median", "cohort_mad", "cohort_n_het_like", "bias_corrected", "bias_source",
    "ad_ref", "ad_alt", "af", "gt",
]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--allelic", required=True, help="GATK CollectAllelicCounts table (<sample>.allelicCounts.tsv)")
    p.add_argument("--catalog", required=True, help="BAF site catalog BED (snp_sites.baf.bed)")
    p.add_argument("--background", required=True, help="cohort background table (baf_background.tsv)")
    p.add_argument("--fai", required=True, help="reference FASTA index (.fai) for the contig header lines")
    p.add_argument("--alleles", default=None,
                   help="optional TSV (contig, pos, ref, alt) giving REF/ALT for catalog sites whose names "
                        "carry none; normally extracted from the phasing reference panel")
    p.add_argument("--sample", required=True, help="sample name for the VCF column")
    p.add_argument("--contig", default="chr17", help="contig to export [chr17]")
    p.add_argument("--output", required=True, help="output VCF (plain text)")
    p.add_argument("--sites-out", required=True, help="output per-site table (TSV)")
    p.add_argument("--summary-out", default=None, help="optional key=value summary file")
    p.add_argument("--min-depth", type=int, default=20, help="minimum raw depth [20]")
    p.add_argument("--hom-ref-max", type=float, default=0.15, help="alt fraction at or below which GT is 0/0 [0.15]")
    p.add_argument("--hom-alt-min", type=float, default=0.85, help="alt fraction at or above which GT is 1/1 [0.85]")
    p.add_argument("--bias-band", type=float, nargs=2, default=(0.35, 0.65), metavar=("LOW", "HIGH"),
                   help="cohort median range treated as het-like for bias correction [0.35 0.65]")
    p.add_argument("--bias-max-mad", type=float, default=0.10, help="maximum cohort MAD for bias correction [0.10]")
    p.add_argument("--bias-min-het", type=int, default=3, help="minimum het-like normals for bias correction [3]")
    p.add_argument("--require-alleles", action="store_true",
                   help="drop sites absent from the --alleles table (use with a panel-derived table)")
    p.add_argument("--global-bias", choices=["auto", "none"], default="auto",
                   help="sample-level bias fallback for sites without a cohort term [auto]")
    p.add_argument("--global-bias-min-depth", type=int, default=50, help="depth floor for the global estimate [50]")
    p.add_argument("--no-bias-correction", action="store_true", help="write raw counts as AD")
    p.add_argument("--all-contigs", action="store_true", help="write every .fai contig to the header, not just --contig")
    return p.parse_args(argv)


def read_catalog(path, contig):
    """Return ({pos: (name, ref, alt)}, [(start, end, name)], [malformed names]) for the contig.

    1-bp rows become sites (ref/alt from a het_ name, else None); longer rows are windows whose
    SNP position is resolved later from the background table. Malformed rows are het_ names
    whose contig/pos disagree with the coordinates."""
    sites = {}
    windows = []
    malformed = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 4 or fields[0] != contig:
                continue
            start, end, name = int(fields[1]), int(fields[2]), fields[3]
            if end - start != 1:
                windows.append((start, end, name))
                continue
            pos = end  # 1-bp BED interval: 1-based position is the end coordinate
            m = CATALOG_NAME_RE.match(name)
            if m:
                if m.group(1) != contig or int(m.group(2)) != pos:
                    malformed.append(name)
                    continue
                sites[pos] = (name, m.group(3), m.group(4))
            else:
                sites[pos] = (name, None, None)
    return sites, windows, malformed


def resolve_windows(sites, windows, background_informative, alleles):
    """Add sites inside each window: table positions when an alleles table is given, else
    informative background positions, else the window centre. Returns a tally dict and the
    pos_source map."""
    pos_source = {}
    tally = {"window_sites_table": 0, "window_sites_background": 0, "window_sites_centre": 0,
             "windows_without_table_site": 0}
    informative = sorted(background_informative)
    table_positions = sorted(alleles)
    for start, end, name in sorted(windows):
        if alleles:
            inside = [p for p in table_positions if start < p <= end and p not in sites]
            if not inside:
                tally["windows_without_table_site"] += 1
                continue
            source = "table"
            tally["window_sites_table"] += len(inside)
        else:
            inside = [p for p in informative if start < p <= end and p not in sites]
            if inside:
                source = "background"
                tally["window_sites_background"] += len(inside)
            else:
                inside = [start + 61] if (start + 61) not in sites else []
                source = "window_centre"
                tally["window_sites_centre"] += len(inside)
        for p in inside:
            label = name if len(inside) == 1 else "%s_%d" % (name, p)
            sites[p] = (label, None, None)
            pos_source[p] = source
    return tally, pos_source


def estimate_global_bias(allelic_path, catalog_path, exclude_contig, min_depth, band=(0.2, 0.8)):
    """Median raw alt fraction of het-like 1-bp backbone sites (alleles in the name) on the
    autosomes other than exclude_contig. Returns (median or None, n_sites)."""
    wanted = {}
    with open(catalog_path) as fh:
        for line in fh:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 4:
                continue
            contig, start, end, name = fields[0], int(fields[1]), int(fields[2]), fields[3]
            if contig == exclude_contig or contig in ("chrX", "chrY", "chrM", "X", "Y", "MT"):
                continue
            m = CATALOG_NAME_RE.match(name)
            if m and end - start == 1:
                wanted[(contig, end)] = (m.group(3), m.group(4))
    afs = []
    header = None
    with open(allelic_path) as fh:
        for line in fh:
            if line.startswith("@") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if header is None:
                header = {name: i for i, name in enumerate(fields)}
                continue
            key = (fields[header["CONTIG"]], int(fields[header["POSITION"]]))
            site = wanted.get(key)
            if site is None:
                continue
            ref_count, alt_count = int(fields[header["REF_COUNT"]]), int(fields[header["ALT_COUNT"]])
            depth = ref_count + alt_count
            if depth < min_depth or fields[header["REF_NUCLEOTIDE"]].upper() != site[0]:
                continue
            if alt_count and fields[header["ALT_NUCLEOTIDE"]].upper() != site[1]:
                continue
            af = alt_count / depth
            if band[0] <= af <= band[1]:
                afs.append(af)
    if len(afs) < 20:
        return None, len(afs)
    afs.sort()
    n = len(afs)
    median = afs[n // 2] if n % 2 else 0.5 * (afs[n // 2 - 1] + afs[n // 2])
    return median, n


def read_alleles(path, contig):
    """Return {pos: (ref, alt)} from a contig/pos/ref/alt table (header line optional)."""
    alleles = {}
    if not path:
        return alleles
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 4 or fields[0] != contig:
                continue
            try:
                pos = int(fields[1])
            except ValueError:
                continue  # header line
            ref, alt = fields[2].upper(), fields[3].upper()
            if len(ref) == 1 and len(alt) == 1 and ref in "ACGT" and alt in "ACGT" and ref != alt:
                alleles[pos] = (ref, alt)
    return alleles


def read_background(path, contig):
    """Return ({pos: (median, mad, n_het_like)}, set of informative positions) for the contig."""
    background = {}
    informative = set()
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if header is None:
                header = {name: i for i, name in enumerate(fields)}
                for col in ("contig", "position", "median_alt_fraction", "mad_alt_fraction", "n_het_like"):
                    if col not in header:
                        sys.exit("[error] background table lacks column '%s'" % col)
                continue
            if fields[header["contig"]] != contig:
                continue
            pos = int(fields[header["position"]])
            if "informative" in header and fields[header["informative"]].strip().lower() == "true":
                informative.add(pos)
            try:
                median = float(fields[header["median_alt_fraction"]])
                mad = float(fields[header["mad_alt_fraction"]])
                n_het = int(float(fields[header["n_het_like"]]))
            except ValueError:
                continue  # NA rows carry no usable bias term
            background[pos] = (median, mad, n_het)
    return background, informative


def read_allelic_counts(path, contig):
    """Return {pos: (ref_count, alt_count, ref_nuc, alt_nuc)} for the contig."""
    counts = {}
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("@") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if header is None:
                header = {name: i for i, name in enumerate(fields)}
                for col in ("CONTIG", "POSITION", "REF_COUNT", "ALT_COUNT", "REF_NUCLEOTIDE", "ALT_NUCLEOTIDE"):
                    if col not in header:
                        sys.exit("[error] allelic counts table lacks column '%s'" % col)
                continue
            if fields[header["CONTIG"]] != contig:
                continue
            counts[int(fields[header["POSITION"]])] = (
                int(fields[header["REF_COUNT"]]),
                int(fields[header["ALT_COUNT"]]),
                fields[header["REF_NUCLEOTIDE"]].upper(),
                fields[header["ALT_NUCLEOTIDE"]].upper(),
            )
    return counts


def read_fai(path):
    """Return [(name, length)] in .fai order."""
    contigs = []
    with open(path) as fh:
        for line in fh:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 2:
                contigs.append((fields[0], int(fields[1])))
    return contigs


def correct_counts(ref_count, alt_count, median):
    """Rescale counts so a het site with cohort median alt fraction `median` centres at 0.5.

    Returns integer (ref, alt) with the same sum as the input.
    """
    depth = ref_count + alt_count
    if depth == 0:
        return ref_count, alt_count
    ref_scaled = ref_count * 0.5 / (1.0 - median)
    alt_scaled = alt_count * 0.5 / median
    total = ref_scaled + alt_scaled
    if total <= 0:
        return ref_count, alt_count
    ref_new = int(round(ref_scaled * depth / total))
    ref_new = max(0, min(depth, ref_new))
    return ref_new, depth - ref_new


def call_gt(af, hom_ref_max, hom_alt_min):
    if af <= hom_ref_max:
        return "0/0"
    if af >= hom_alt_min:
        return "1/1"
    return "0/1"


def fmt(x, digits=4):
    if x is None:
        return "NA"
    if isinstance(x, float):
        return ("%%.%df" % digits) % x
    return str(x)


def main(argv=None):
    args = parse_args(argv)
    band_low, band_high = args.bias_band
    if not (0.0 < band_low < band_high < 1.0):
        sys.exit("[error] --bias-band must satisfy 0 < LOW < HIGH < 1")
    if not (0.0 <= args.hom_ref_max < args.hom_alt_min <= 1.0):
        sys.exit("[error] --hom-ref-max must be below --hom-alt-min")

    catalog, windows, malformed = read_catalog(args.catalog, args.contig)
    if malformed:
        sys.stderr.write("[warn] %d malformed catalog rows on %s were skipped (first: %s)\n"
                         % (len(malformed), args.contig, malformed[0]))
    alleles = read_alleles(args.alleles, args.contig)
    background, informative = read_background(args.background, args.contig)
    window_tally, pos_source = resolve_windows(catalog, windows, informative, alleles)
    if not catalog:
        sys.exit("[error] no catalog sites on %s in %s" % (args.contig, args.catalog))
    global_bias, global_n = (None, 0)
    if args.global_bias == "auto" and not args.no_bias_correction:
        global_bias, global_n = estimate_global_bias(args.allelic, args.catalog, args.contig,
                                                     args.global_bias_min_depth)
        if global_bias is not None and not (0.40 <= global_bias <= 0.55):
            sys.stderr.write("[warn] global bias estimate %.3f (n=%d) outside 0.40-0.55; not applied\n"
                             % (global_bias, global_n))
            global_bias = None
    counts = read_allelic_counts(args.allelic, args.contig)
    fai = read_fai(args.fai)
    fai_names = [name for name, _ in fai]
    if args.contig not in fai_names:
        sys.exit("[error] contig %s not in %s" % (args.contig, args.fai))
    header_contigs = fai if args.all_contigs else [c for c in fai if c[0] == args.contig]

    tally = {
        "catalog_sites": len(catalog), "written": 0, "het": 0, "hom_ref": 0, "hom_alt": 0,
        "bias_corrected": 0, "NOT_IN_COUNTS": 0, "LOW_DEPTH": 0, "REF_MISMATCH": 0, "ALT_MISMATCH": 0,
        "ALT_UNKNOWN": 0, "ALLELE_CONFLICT": 0, "alt_base_ignored": 0,
        "alleles_from_name": 0, "alleles_from_table": 0, "alleles_from_counts": 0,
        "catalog_windows": len(windows), "NOT_IN_TABLE": 0, "bias_cohort": 0, "bias_global": 0,
    }
    tally.update(window_tally)
    vcf_rows = []
    site_rows = []

    for pos in sorted(catalog):
        name, ref, alt = catalog[pos]
        table = alleles.get(pos)
        source = "name" if ref else ("table" if table else "counts")
        if ref and table and (ref, alt) != table:
            row = {"contig": args.contig, "pos": pos, "id": name, "ref": ref, "alt": alt,
                   "allele_source": "name+table", "pos_source": pos_source.get(pos, "catalog"),
                   "status": "ALLELE_CONFLICT", "bias_corrected": "false"}
            tally["ALLELE_CONFLICT"] += 1
            site_rows.append(row)
            continue
        if not ref and table:
            ref, alt = table
        row = {"contig": args.contig, "pos": pos, "id": name, "ref": ref, "alt": alt, "allele_source": source,
               "pos_source": pos_source.get(pos, "catalog")}
        bg = background.get(pos)
        row["cohort_median"], row["cohort_mad"], row["cohort_n_het_like"] = (bg if bg else (None, None, None))
        row["bias_corrected"] = "false"
        row["bias_source"] = "none"
        if args.require_alleles and alleles and table is None:
            row["status"] = "NOT_IN_TABLE"
            tally["NOT_IN_TABLE"] += 1
            site_rows.append(row)
            continue

        entry = counts.get(pos)
        if entry is None:
            row["status"] = "NOT_IN_COUNTS"
            tally["NOT_IN_COUNTS"] += 1
            site_rows.append(row)
            continue
        raw_ref, raw_alt, ref_nuc, alt_nuc = entry
        depth = raw_ref + raw_alt
        row.update({"raw_ref": raw_ref, "raw_alt": raw_alt, "depth": depth,
                    "raw_af": (raw_alt / depth) if depth else None})

        if ref is None:
            # No alleles from the name or the table: take REF from the counts and ALT from the
            # observed non-reference base, which only exists when the site is not hom-ref.
            ref = ref_nuc
            row["ref"] = ref
            if depth and raw_alt / depth > args.hom_ref_max and alt_nuc in "ACGT" and alt_nuc != ref:
                alt = alt_nuc
                row["alt"] = alt
            else:
                row["alt"] = None
                row["status"] = "ALT_UNKNOWN" if depth >= args.min_depth else "LOW_DEPTH"
                tally[row["status"]] += 1
                site_rows.append(row)
                continue
        if ref_nuc != ref:
            row["status"] = "REF_MISMATCH"
            tally["REF_MISMATCH"] += 1
            site_rows.append(row)
            continue
        if depth < args.min_depth:
            row["status"] = "LOW_DEPTH"
            tally["LOW_DEPTH"] += 1
            site_rows.append(row)
            continue
        if raw_alt > 0 and alt_nuc != alt:
            # The counts table reports the most frequent non-reference base; when that is not
            # the catalog ALT, the catalog ALT count is at most raw_alt and effectively zero.
            if raw_alt / depth <= args.hom_ref_max:
                raw_alt = 0
                raw_ref = depth
                row["raw_alt"] = 0
                row["raw_ref"] = depth
                row["raw_af"] = 0.0
                tally["alt_base_ignored"] += 1
            else:
                row["status"] = "ALT_MISMATCH"
                tally["ALT_MISMATCH"] += 1
                site_rows.append(row)
                continue

        ad_ref, ad_alt = raw_ref, raw_alt
        if (not args.no_bias_correction and bg is not None
                and band_low <= bg[0] <= band_high and bg[1] <= args.bias_max_mad
                and bg[2] >= args.bias_min_het):
            ad_ref, ad_alt = correct_counts(raw_ref, raw_alt, bg[0])
            row["bias_corrected"] = "true"
            row["bias_source"] = "cohort"
            tally["bias_corrected"] += 1
            tally["bias_cohort"] += 1
        elif not args.no_bias_correction and global_bias is not None:
            ad_ref, ad_alt = correct_counts(raw_ref, raw_alt, global_bias)
            row["bias_corrected"] = "true"
            row["bias_source"] = "global"
            tally["bias_corrected"] += 1
            tally["bias_global"] += 1
        af = ad_alt / depth
        gt = call_gt(af, args.hom_ref_max, args.hom_alt_min)
        row.update({"status": "OK", "ad_ref": ad_ref, "ad_alt": ad_alt, "af": af, "gt": gt})
        tally["written"] += 1
        tally["alleles_from_" + source] += 1
        tally[{"0/1": "het", "0/0": "hom_ref", "1/1": "hom_alt"}[gt]] += 1
        site_rows.append(row)
        vcf_rows.append("\t".join([
            args.contig, str(pos), name, ref, alt, ".", "PASS", ".", "GT:AD:DP:RAD",
            "%s:%d,%d:%d:%d,%d" % (gt, ad_ref, ad_alt, depth, raw_ref, raw_alt),
        ]))

    with open(args.output, "w") as out:
        out.write("##fileformat=VCFv4.2\n")
        out.write("##source=%s\n" % VERSION)
        out.write("##baf_genotypes_vcf_params=<contig=%s,min_depth=%d,hom_ref_max=%.3f,hom_alt_min=%.3f,"
                  "bias_band=%.2f-%.2f,bias_max_mad=%.3f,bias_min_het=%d,bias_correction=%s>\n"
                  % (args.contig, args.min_depth, args.hom_ref_max, args.hom_alt_min, band_low, band_high,
                     args.bias_max_mad, args.bias_min_het, "false" if args.no_bias_correction else "true"))
        out.write("##baf_genotypes_vcf_global_bias=<median_het_af=%s,n_sites=%d,applied=%s>\n"
                  % ("NA" if global_bias is None else "%.4f" % global_bias, global_n,
                     "true" if global_bias is not None else "false"))
        for name, length in header_contigs:
            out.write("##contig=<ID=%s,length=%d>\n" % (name, length))
        out.write('##FILTER=<ID=PASS,Description="All filters passed">\n')
        out.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype called from the alt fraction">\n')
        out.write('##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths for the ref and alt alleles '
                  'after cohort reference-bias correction">\n')
        out.write('##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth (sum of AD)">\n')
        out.write('##FORMAT=<ID=RAD,Number=R,Type=Integer,Description="Raw allelic depths before correction">\n')
        out.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t%s\n" % args.sample)
        for line in vcf_rows:
            out.write(line + "\n")

    with open(args.sites_out, "w") as out:
        out.write("\t".join(SITE_COLUMNS) + "\n")
        for row in site_rows:
            out.write("\t".join(fmt(row.get(col)) for col in SITE_COLUMNS) + "\n")

    summary_keys = ["catalog_sites", "catalog_windows", "window_sites_table", "window_sites_background",
                    "window_sites_centre", "windows_without_table_site",
                    "written", "het", "hom_ref", "hom_alt", "bias_corrected", "bias_cohort", "bias_global",
                    "alleles_from_name", "alleles_from_table", "alleles_from_counts", "alt_base_ignored",
                    "NOT_IN_COUNTS", "LOW_DEPTH", "REF_MISMATCH", "ALT_MISMATCH", "ALT_UNKNOWN",
                    "ALLELE_CONFLICT", "NOT_IN_TABLE"]
    summary = ["sample=%s" % args.sample, "contig=%s" % args.contig] + ["%s=%d" % (k, tally[k]) for k in summary_keys]
    summary.append("global_bias_median_het_af=%s" % ("NA" if global_bias is None else "%.4f" % global_bias))
    summary.append("global_bias_n_sites=%d" % global_n)
    if args.summary_out:
        with open(args.summary_out, "w") as out:
            out.write("\n".join(summary) + "\n")
    sys.stderr.write("[baf_genotypes_vcf] " + " ".join(summary) + "\n")
    if tally["written"] == 0:
        sys.exit("[error] no site written for %s" % args.contig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
