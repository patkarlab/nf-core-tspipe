"""Parse somaticseq variant TSVs.

Two flavors with overlapping schemas:
  - clinical_final.tsv : curated clinical variants (smaller column set, PASS/REJECT verdict)
  - filtered.tsv       : full annotated set (adds ClinVar, gnomAD AF, etc.)

Both are simple tab-delimited with a header row. We use pandas for robustness
to mixed types and to support the front-end (DataTables) consuming JSON-friendly rows.

Returned shape:
  {
    'columns': [list of column names in source order],
    'rows':    [list of dicts, one per variant],
    'n':       int row count,
    'n_pass':  int rows with SomaticSeq_Verdict == 'PASS' (clinical only; None otherwise)
  }

Returns None if the file is missing or unreadable.
"""

from pathlib import Path

import pandas as pd


def parse(path):
    path = Path(path)
    if not path.exists():
        return None

    try:
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_values=[""])
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None

    if df.empty:
        return {"columns": list(df.columns), "rows": [], "n": 0, "n_pass": None}

    # Fill NaN -> '' for JSON-friendliness; templates use truthiness checks.
    df = df.fillna("")
    columns = list(df.columns)
    rows = df.to_dict(orient="records")

    n_pass = None
    if "SomaticSeq_Verdict" in df.columns:
        n_pass = int((df["SomaticSeq_Verdict"] == "PASS").sum())

    return {"columns": columns, "rows": rows, "n": len(rows), "n_pass": n_pass}


def best_hgvsp(row):
    """DASH_HGVS_PREF_V1 (D3b): VariantValidator -> CAVA (MANE 1.5 RefSeq) -> VEP."""
    for col in ("VV_HGVSp", "CAVA_HGVSp", "HGVSp"):
        v = row.get(col, "")
        if v and v != "-1":
            return v
    return ""
