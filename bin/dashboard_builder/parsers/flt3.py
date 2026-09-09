"""Parse FLT3-ITD consensus output.

flt3_consensus.tsv columns:
  sample, status, n_tools, tools, length_bp, length_range, pos_hg38,
  vaf_pct_min, vaf_pct_max, vaf_pct_mean, ar_min, ar_max, ar_mean,
  hgvsc, hgvsp, domain, inserted_seq, raw_calls

Returns:
  {
    'rows': [list of dicts],
    'n_positive': int rows with status indicating ITD detected (any non-empty status that is not 'negative')
  }
or None if the file is missing/unreadable.

Note: when the file has only a header (no rows), the sample is FLT3-ITD negative.
"""

from pathlib import Path

import pandas as pd


# IGV_V2A: FLT3 insertion-site regions (Rücker et al., Blood 2022), amino-acid coordinates on
# NP_004110. Residues above 630 fall in the rest of TKD1; below 572 is upstream of the JM domain.
_FLT3_REGIONS = [
    (572, 578, "JM-B"), (579, 592, "JM-S"), (593, 603, "JM-Z"), (604, 609, "HR"),
    (610, 615, "beta1-sheet"), (616, 623, "NBL"), (624, 630, "beta2-sheet"),
]


def _flt3_region(aa):
    for lo, hi, name in _FLT3_REGIONS:
        if lo <= aa <= hi:
            return name
    return "TKD1 (beyond beta2)" if aa > 630 else "upstream of JM"


def _domain_from_hgvsp(hgvsp):
    """'p.585_610dup' -> 'p.585-610: JM-S -> beta1-sheet'. Empty when HGVSp is not a
    residue-range duplication (the tools report other shapes for some events)."""
    import re
    m = re.search(r"p\.(?:\(?)(?:[A-Za-z]{0,3})(\d+)_(?:[A-Za-z]{0,3})(\d+)dup", str(hgvsp or ""))
    if not m:
        return ""
    a, b = int(m.group(1)), int(m.group(2))
    ra, rb = _flt3_region(a), _flt3_region(b)
    span = ra if ra == rb else "%s -> %s" % (ra, rb)
    return "p.%d-%d: %s" % (a, b, span)


def parse(path):
    path = Path(path)
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_values=[""])
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None

    df = df.fillna("")
    rows = df.to_dict(orient="records")
    for r in rows:   # IGV_V2A: domain span from HGVSp when the tools left the field empty
        r["domain_derived"] = _domain_from_hgvsp(r.get("hgvsp", ""))

    n_positive = 0
    if "status" in df.columns:
        # Treat anything that is non-empty and not "negative"/"no_itd" as a positive event.
        statuses = df["status"].str.lower()
        n_positive = int((statuses.notna() & (statuses != "") & (~statuses.isin(["negative", "no_itd", "no-itd"]))).sum())

    return {"rows": rows, "n_positive": n_positive, "n_total": len(rows)}
