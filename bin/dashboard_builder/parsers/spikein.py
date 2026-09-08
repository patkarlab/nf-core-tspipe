"""Parse spike-in regions and SNP genotypes for the Spike-in tab (SPIKEIN_V1, D13).

Inputs
  asset_path      assets/<panel>/spikein_regions.tsv (None -> tab not rendered)
  coverage_path   clinical/<sample>_exon_coverage.tsv (region coverage; Gene == region name, Exon == "-")
  snps_path       clinical/<sample>.spikein_snps.tsv from SPIKEIN_SITES (may be absent)
  filtered        ctx["filtered"] (the parsed somaticseq.filtered.tsv; rows keep their Filter value)

Returns None when there is no asset, else a dict:
  regions   list of region dicts with coverage and the filtered rows inside them
  region_variants  the same rows flattened, each with a "region" key
  region_keys      Chr:Start:Ref:Alt of those rows, for the client-side variant browser (SPIKEIN_V1c)
  snps      list of SNP dicts (SPIKEIN_SITES row + the filtered row at that site, if any)
  n_variants, n_pass, n_low_regions, tier_x, min_depth
Region variants are shown WITH their Filter value on purpose: the consequence
filter hides 5'UTR/intronic calls from the clinical table, and this tab is
where a reviewer sees them.
"""

from pathlib import Path

ASSET_PATH = None     # set by build.py from --spikein-regions
TIER_X = 200          # reportability tier used by coverage.verdict() (DASH_QC_V1)
MIN_DEPTH = 20        # SNP call threshold, mirrors bin/spikein_sites.py

_ROW_KEYS = ("Chr", "Start", "Ref", "Alt", "Gene", "HGVSc", "HGVSp", "Consequence",
             "Variant_Class", "VAF_pct", "Callers", "VariantCaller_Count", "Filter",
             "Max_AF", "rsID", "ClinVar_Significance")


def _read_tsv(path, comment="#"):
    p = Path(path) if path else None
    if p is None or not p.exists():
        return []
    rows = []
    header = None
    with open(p) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or (comment and line.startswith(comment)):
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    return rows


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _slim(row):
    out = {}
    for k in _ROW_KEYS:
        v = row.get(k, "")
        out[k] = "" if v in (None, "-1", ".") else v
    return out


def parse(asset_path, coverage_path=None, snps_path=None, filtered=None):
    asset = _read_tsv(asset_path)
    if not asset:
        return None

    cov = {}
    for r in _read_tsv(coverage_path, comment=None):
        if r.get("Exon", "") in ("-", "", None):
            cov[r.get("Gene", "")] = r

    frows = (filtered or {}).get("rows") if isinstance(filtered, dict) else None
    frows = frows or []

    def rows_in(chrom, start0, end):
        hits = []
        for r in frows:
            if r.get("Chr") != chrom:
                continue
            s = _num(r.get("Start"))
            if s is None:
                continue
            if start0 < s <= end:
                hits.append(_slim(r))
        hits.sort(key=lambda d: _num(d.get("Start")) or 0)
        return hits

    regions = []
    region_variants = []
    n_variants = 0
    n_pass = 0
    n_low = 0
    for a in asset:
        if a.get("class") != "regulatory":
            continue
        start0, end = int(a["start"]), int(a["end"])
        c = cov.get(a["name"], {})
        mean = _num(c.get("Mean_Coverage"))
        variants = rows_in(a["chrom"], start0, end)
        n_variants += len(variants)
        n_pass += sum(1 for v in variants if v.get("Filter") == "PASS")
        for v in variants:
            fv = dict(v)
            fv["region"] = a["name"]
            region_variants.append(fv)
        tier = None if mean is None else (mean >= TIER_X)
        if tier is False:
            n_low += 1
        regions.append({
            "name": a["name"], "gene": a.get("gene", ""), "chrom": a["chrom"],
            "start": start0 + 1, "end": end, "length": end - start0,
            "description": a.get("description", ""),
            "mean_cov": mean,
            "pct_100x": _num(c.get("Pct_100x")),
            "pct_250x": _num(c.get("Pct_250x")),
            "pct_500x": _num(c.get("Pct_500x")),
            "has_coverage": bool(c),
            "at_tier": tier,
            "variants": variants,
        })

    snps = []
    snp_rows = {r.get("name"): r for r in _read_tsv(snps_path, comment=None)}
    for a in asset:
        if a.get("class") != "germline_snp":
            continue
        s = dict(snp_rows.get(a["name"], {}))
        pos = int(a["pos"])
        at_site = [v for v in rows_in(a["chrom"], pos - 1, pos)]
        s.update({
            "name": a["name"], "gene": a.get("gene", ""), "chrom": a["chrom"], "pos": pos,
            "rsid": a.get("rsid", ""), "rsid_alias": a.get("rsid_alias", "-"),
            "risk_allele": a.get("risk_allele", "-"), "description": a.get("description", ""),
            "status": s.get("status", "NOT_RUN"),
            "depth_num": _num(s.get("depth")),
            "filtered_row": at_site[0] if at_site else None,
        })
        snps.append(s)

    return {
        "regions": regions, "region_variants": region_variants, "snps": snps,
        "region_keys": ["%s:%s:%s:%s" % (v.get("Chr", ""), v.get("Start", ""), v.get("Ref", ""), v.get("Alt", "")) for v in region_variants],
        "n_regions": len(regions), "n_snps": len(snps),
        "n_variants": n_variants, "n_pass": n_pass, "n_low_regions": n_low,
        "tier_x": TIER_X, "min_depth": MIN_DEPTH,
    }
