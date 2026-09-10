"""TP53 / 17p observation block (TP53_OBS_V1).

Puts the reportable TP53 variant(s) and the 17p allelic evidence side by side
as OBSERVATIONS. The interpretation line is looked up in a rule table that the
reporting pathologist owns (assets/<panel>/tp53_interpretation_rules.tsv); this
module never derives "multi-hit" or any other classification on its own.

Inputs (everything is already under clinical/; nothing is recomputed)
  clinical        ctx["clinical"] as parsed by parsers.variants (somaticseq.clinical.final.tsv)
  sample_dir      clinical/ of the sample (the --subdir directory)
                    cnv/consensus/<S>.cnv_consensus4.genes.tsv   TP53 row: consensus + per-arm columns
                    cnv/consensus/<S>.cnv_consensus4.json        purecn / purple summaries, baf_arms fallback
                    cnv/baf/<S>.baf.summary.tsv                  BAF_V2 17p arm row
                    cnv/purple/<S>.purple.h_summary.tsv          PURPLE purity, status, trusted
  rules_path      the rule table (None or missing file -> "per reporting pathologist")

Returns None when neither a clinical table nor a consensus table is available,
otherwise a dict:
  variants        list of TP53 rows (slimmed; HGVS by VariantValidator -> CAVA -> VEP)
  n_variants      TP53 rows in the clinical table (the table is already the reportable set)
  n_variants_pass rows with SomaticSeq_Verdict == PASS
  cnv             TP53 consensus row fields (consensus_call, tier, flags, allelic_state, arm columns)
  baf             BAF_V2 17p arm row (verdict, f, n_het, confidence, scope, cr)
  purity          {purple, purple_status, purple_trusted, purecn, purecn_flagged, purecn_comment}
  facts           the flat field set the rule conditions are evaluated on (also shown for audit)
  observations    list of one-line factual strings
  interpretation  {wording, condition, source} - the first matching rule, or the default line
  rules           {path, n, error}
Standard library only; Python 3.6+ syntax.
"""

import csv
import json
import re
from pathlib import Path

RULES_PATH = None            # set by build.py from --tp53-rules
GENE = "TP53"
ARM = "17p"
DEFAULT_WORDING = "per reporting pathologist"

# Fields a rule condition may reference. Kept explicit so an unknown field in a
# rule is reported instead of silently never matching.
FACT_FIELDS = (
    "n_variants", "n_variants_pass", "max_vaf", "min_vaf",
    "cnv_call", "cnv_tier", "cnv_flags", "allelic_state",
    "k_call", "k_cn", "k_log2", "g_call", "g_seg_log2", "b_call",
    "p_call", "p_C", "p_loh", "e_call",
    "h_call", "h_cn_min", "h_cn_max", "h_macn_min", "h_loh",
    "baf_verdict", "baf_confidence", "baf_f", "baf_n_het", "baf_scope", "baf_cr",
    "purity", "purple_status", "purple_trusted", "purecn_purity",
)

_CLAUSE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|>=|<=|>|<|\bnotin\b|\bin\b)\s*(?![=<>!])(.+?)\s*$")


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def _read_tsv(path):
    p = Path(path) if path else None
    if p is None or not p.exists():
        return []
    with open(str(p)) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _clean(v):
    if v is None:
        return ""
    v = str(v).strip()
    return "" if v in ("-1", ".", "NA", "nan", "None") else v


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v, nd=2):
    n = _num(v)
    if n is None:
        return _clean(v)
    return "%.*f" % (nd, n)


def _first(row, keys):
    for k in keys:
        v = _clean(row.get(k, ""))
        if v:
            return v, k
    return "", ""


# ----------------------------------------------------------------------------
# variants
# ----------------------------------------------------------------------------
def _transcript(r, src_col, hgvsc):
    """Transcript from the same source as the chosen HGVSc (never mix sources)."""
    if src_col == "VV_HGVSc":
        return _clean(r.get("VV_Transcript", ""))
    if src_col == "CAVA_HGVSc":
        return _clean(r.get("CAVA_Transcript", ""))
    return hgvsc.split(":", 1)[0] if ":" in hgvsc else ""


def _slim_variant(r):
    hgvsc, src_c = _first(r, ("VV_HGVSc", "CAVA_HGVSc", "HGVSc"))
    hgvsp, src_p = _first(r, ("VV_HGVSp", "CAVA_HGVSp", "HGVSp"))
    src = {"VV_HGVSc": "VariantValidator", "CAVA_HGVSc": "CAVA", "HGVSc": "VEP"}.get(src_c, "")
    key = "%s:%s:%s:%s" % (r.get("Chr", ""), r.get("Start", ""), r.get("Ref", ""), r.get("Alt", ""))
    vaf = _num(r.get("VAF_pct"))
    return {
        "key": key,
        "chr": r.get("Chr", ""), "pos": r.get("Start", ""), "ref": r.get("Ref", ""), "alt": r.get("Alt", ""),
        "hgvsc": hgvsc, "hgvsp": hgvsp, "hgvs_source": src,
        "transcript": _transcript(r, src_c, hgvsc),
        "exon": _clean(r.get("VV_Exon", "")),
        "consequence": _clean(r.get("Consequence", "")),
        "variant_class": _clean(r.get("Variant_Class", "")),
        "vaf": vaf, "vaf_str": "" if vaf is None else "%.1f" % vaf,
        "ref_count": _clean(r.get("REF_COUNT", "")), "alt_count": _clean(r.get("ALT_COUNT", "")),
        "callers": _clean(r.get("Callers", "")), "n_callers": _clean(r.get("VariantCaller_Count", "")),
        "verdict": _clean(r.get("SomaticSeq_Verdict", "")),
        "filter": _clean(r.get("Filter", "")),
        "clinvar": _clean(r.get("ClinVar", "")),
        "cosmic": _clean(r.get("COSMIC_ID", "")),
        "oncovi": _clean(r.get("OncoVI_Classification", "")),
        "oncovi_score": _clean(r.get("OncoVI_Score", "")),
        "mnv_note": _clean(r.get("MNV_Note", "")),
        "max_af": _clean(r.get("Max_AF", "")),
    }


def _tp53_variants(clinical):
    rows = (clinical or {}).get("rows") if isinstance(clinical, dict) else None
    out = []
    for r in rows or []:
        if str(r.get("Gene", "")).strip() == GENE:
            out.append(_slim_variant(r))
    out.sort(key=lambda d: (-(d["vaf"] if d["vaf"] is not None else -1.0), d["pos"]))
    return out


# ----------------------------------------------------------------------------
# 17p evidence
# ----------------------------------------------------------------------------
_CNV_KEYS = ("gene", "chrom", "start", "end", "cytoband", "consensus_call", "tier", "flags", "support",
             "allelic_state", "k_call", "k_cn", "k_log2", "g_call", "g_seg_log2", "g_n_bins",
             "b_call", "p_call", "p_C", "p_loh", "e_call", "e_bf",
             "h_call", "h_cn_min", "h_cn_max", "h_macn_min", "h_loh",
             "driver_role", "clingen_hi", "loo_fp_any")


def _consensus_rows(sample_dir, sample):
    path = sample_dir / "cnv" / "consensus" / ("%s.cnv_consensus4.genes.tsv" % sample)
    rows = [r for r in _read_tsv(path) if r.get("gene", "") == GENE]
    out = []
    for r in rows:
        d = dict((k, _clean(r.get(k, ""))) for k in _CNV_KEYS)
        for k in ("k_log2", "g_seg_log2", "h_cn_min", "h_cn_max", "h_macn_min"):
            if d.get(k):
                d[k] = _fmt(d[k], 2)
        out.append(d)
    return out


def _consensus_json(sample_dir, sample):
    path = sample_dir / "cnv" / "consensus" / ("%s.cnv_consensus4.json" % sample)
    if not path.exists():
        return {}
    try:
        with open(str(path)) as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def _baf_row(sample_dir, sample, cj):
    rows = None
    for cand in (sample_dir / "cnv" / "baf" / ("%s.baf.summary.tsv" % sample),
                 sample_dir / "cnv" / ("%s.baf.summary.tsv" % sample)):
        if cand.exists():
            rows = _read_tsv(cand)
            break
    if rows is None:
        rows = cj.get("baf_arms") or ([cj["baf17p"]] if cj.get("baf17p") else [])
    for r in rows or []:
        if str(r.get("arm", "")) == ARM:
            return {
                "arm": ARM, "region": _clean(r.get("region", "")),
                "verdict": _clean(r.get("verdict", "")), "confidence": _clean(r.get("confidence", "")) or "NA",
                "scope": _clean(r.get("scope", "")),
                "f": _fmt(r.get("f_estimate", ""), 3), "n_het": _clean(r.get("n_het", "")),
                "n_informative": _clean(r.get("n_informative", "")), "n_covered": _clean(r.get("n_covered", "")),
                "cr": _fmt(r.get("cr_median_log2", ""), 2), "n_cr_bins": _clean(r.get("n_cr_bins", "")),
                "dev": _fmt(r.get("median_mirrored_dev", ""), 3), "noise_floor": _fmt(r.get("noise_floor", ""), 3),
            }
    return None


def _purity(sample_dir, sample, cj):
    out = {"purple": "", "purple_status": "", "purple_trusted": "", "purple_method": "",
           "purecn": "", "purecn_flagged": "", "purecn_comment": ""}
    ps = sample_dir / "cnv" / "purple" / ("%s.purple.h_summary.tsv" % sample)
    rows = _read_tsv(ps)
    src = rows[0] if rows else (cj.get("purple") or {})
    if src:
        out["purple"] = _fmt(src.get("purity", ""), 2)
        out["purple_status"] = _clean(src.get("status", ""))
        out["purple_trusted"] = _clean(src.get("trusted", "")).upper()
        out["purple_method"] = _clean(src.get("method", ""))
    pc = cj.get("purecn") or {}
    if pc:
        out["purecn"] = _fmt(pc.get("purity", ""), 2)
        out["purecn_flagged"] = _clean(pc.get("flagged", "")).upper()
        out["purecn_comment"] = _clean(pc.get("comment", ""))
    return out


# ----------------------------------------------------------------------------
# rule table
# ----------------------------------------------------------------------------
def load_rules(path):
    """Read the rule table. Returns (rules, error). A rule is {condition, wording, note, line}."""
    p = Path(path) if path else None
    if p is None or not p.exists():
        return [], None
    rules = []
    header = None
    try:
        with open(str(p)) as fh:
            for n, line in enumerate(fh, 1):
                line = line.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split("\t")
                if header is None:
                    header = [h.strip() for h in parts]
                    if "condition" not in header or "wording" not in header:
                        return [], "line %d: header must contain 'condition' and 'wording'" % n
                    continue
                row = dict(zip(header, parts))
                cond = (row.get("condition") or "").strip()
                wording = (row.get("wording") or "").strip()
                if not cond or not wording:
                    continue
                rules.append({"condition": cond, "wording": wording,
                              "note": (row.get("note") or "").strip(), "line": n})
    except OSError as exc:
        return [], str(exc)
    return rules, None


def _norm(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v).strip().lower()


def _compare(actual, op, expected):
    """Numeric comparison when both sides parse as numbers, else case-insensitive string."""
    if op in ("in", "notin"):
        wanted = [_norm(x) for x in expected.split(",") if x.strip()]
        hit = _norm(actual) in wanted
        return hit if op == "in" else not hit
    a_num, e_num = _num(actual), _num(expected)
    if a_num is not None and e_num is not None:
        a, e = a_num, e_num
    else:
        if op in (">", "<", ">=", "<="):
            return False           # ordering on non-numbers is undefined: never matches
        a, e = _norm(actual), _norm(expected)
    return {"==": a == e, "!=": a != e, ">": a > e, "<": a < e, ">=": a >= e, "<=": a <= e}[op]


def evaluate(condition, facts):
    """True when every ';'-separated clause holds. Raises ValueError on a malformed clause
    or an unknown field so a typo in the asset is visible, not silently false."""
    cond = condition.strip()
    if cond in ("default", "*"):
        return True
    for clause in cond.split(";"):
        if not clause.strip():
            continue
        m = _CLAUSE.match(clause)
        if not m:
            raise ValueError("cannot parse clause %r" % clause.strip())
        field, op, value = m.group(1), m.group(2).strip(), m.group(3).strip()
        if field not in FACT_FIELDS:
            raise ValueError("unknown field %r (known: %s)" % (field, ", ".join(FACT_FIELDS)))
        if not _compare(facts.get(field), op, value):
            return False
    return True


def interpret(rules, facts):
    """First matching rule wins; malformed rules are skipped and reported."""
    errors = []
    for r in rules:
        try:
            if evaluate(r["condition"], facts):
                return {"wording": r["wording"], "condition": r["condition"], "line": r["line"],
                        "source": "rule"}, errors
        except ValueError as exc:
            errors.append("line %d: %s" % (r["line"], exc))
    return {"wording": DEFAULT_WORDING, "condition": "", "line": None, "source": "default"}, errors


# ----------------------------------------------------------------------------
# facts and observations
# ----------------------------------------------------------------------------
def _facts(variants, cnv, baf, purity):
    vafs = [v["vaf"] for v in variants if v["vaf"] is not None]
    c = cnv or {}
    b = baf or {}
    return {
        "n_variants": len(variants),
        "n_variants_pass": sum(1 for v in variants if v["verdict"] == "PASS"),
        "max_vaf": max(vafs) if vafs else None,
        "min_vaf": min(vafs) if vafs else None,
        "cnv_call": c.get("consensus_call", ""), "cnv_tier": c.get("tier", ""), "cnv_flags": c.get("flags", ""),
        "allelic_state": c.get("allelic_state", ""),
        "k_call": c.get("k_call", ""), "k_cn": c.get("k_cn", ""), "k_log2": c.get("k_log2", ""),
        "g_call": c.get("g_call", ""), "g_seg_log2": c.get("g_seg_log2", ""), "b_call": c.get("b_call", ""),
        "p_call": c.get("p_call", ""), "p_C": c.get("p_C", ""), "p_loh": _norm(c.get("p_loh", "")),
        "e_call": c.get("e_call", ""),
        "h_call": c.get("h_call", ""), "h_cn_min": c.get("h_cn_min", ""), "h_cn_max": c.get("h_cn_max", ""),
        "h_macn_min": c.get("h_macn_min", ""), "h_loh": _norm(c.get("h_loh", "")),
        "baf_verdict": b.get("verdict", ""), "baf_confidence": b.get("confidence", ""),
        "baf_f": b.get("f", ""), "baf_n_het": b.get("n_het", ""), "baf_scope": b.get("scope", ""),
        "baf_cr": b.get("cr", ""),
        "purity": purity.get("purple", ""), "purple_status": purity.get("purple_status", ""),
        "purple_trusted": purity.get("purple_trusted", ""), "purecn_purity": purity.get("purecn", ""),
    }


def _observations(variants, cnv, baf, purity):
    obs = []
    if not variants:
        obs.append("No reportable TP53 variant in the clinical table.")
    else:
        parts = []
        for v in variants:
            lab = v["hgvsp"] or v["hgvsc"] or v["key"]
            bits = [lab]
            if v["vaf_str"]:
                bits.append("VAF %s %%" % v["vaf_str"])
            if v["n_callers"]:
                bits.append("%s caller(s)" % v["n_callers"])
            if v["verdict"] and v["verdict"] != "PASS":
                bits.append(v["verdict"])
            parts.append(", ".join(bits))
        obs.append("%d reportable TP53 variant%s: %s." % (len(variants), "" if len(variants) == 1 else "s",
                                                          "; ".join(parts)))
    if cnv:
        seg = ["17p (TP53) consensus %s%s%s" % (
            cnv.get("consensus_call") or "n/a",
            (" " + cnv["tier"]) if cnv.get("tier") else "",
            (" [%s]" % cnv["flags"]) if cnv.get("flags") and cnv["flags"] != "-" else "")]
        if cnv.get("k_call"):
            seg.append("CNVkit %s cn %s (log2 %s)" % (cnv["k_call"], cnv.get("k_cn") or "?", cnv.get("k_log2") or "?"))
        if cnv.get("g_call"):
            seg.append("GATK %s" % cnv["g_call"])
        if cnv.get("h_call"):
            seg.append("PURPLE %s total %s-%s / minor %s, LOH %s" % (
                cnv["h_call"], cnv.get("h_cn_min") or "?", cnv.get("h_cn_max") or "?",
                cnv.get("h_macn_min") or "?", cnv.get("h_loh") or "?"))
        if cnv.get("p_call"):
            seg.append("PureCN %s C %s, LOH %s" % (cnv["p_call"], cnv.get("p_C") or "?", cnv.get("p_loh") or "?"))
        obs.append("; ".join(seg) + ".")
    if baf:
        s = "BAF_V2 17p %s" % (baf.get("verdict") or "n/a")
        if baf.get("f"):
            s += " f %s" % baf["f"]
        s += " (%s het sites, confidence %s, scope %s, copy ratio %s)" % (
            baf.get("n_het") or "?", baf.get("confidence") or "?", baf.get("scope") or "?", baf.get("cr") or "?")
        obs.append(s + ".")
    pur = []
    if purity.get("purple"):
        pur.append("PURPLE %s (%s%s)" % (purity["purple"], purity.get("purple_status") or "?",
                                          "" if purity.get("purple_trusted") == "TRUE" else ", advisory"))
    if purity.get("purecn"):
        pur.append("PureCN %s%s" % (purity["purecn"], (" (%s)" % purity["purecn_comment"]) if purity.get("purecn_comment") else ""))
    if pur:
        obs.append("Purity: " + "; ".join(pur) + ".")
    return obs


# ----------------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------------
def parse(sample_dir, sample, clinical=None, rules_path=None):
    sample_dir = Path(sample_dir)
    variants = _tp53_variants(clinical)
    cnv_rows = _consensus_rows(sample_dir, sample)
    if clinical is None and not cnv_rows:
        return None
    cj = _consensus_json(sample_dir, sample)
    cnv = cnv_rows[0] if cnv_rows else None
    baf = _baf_row(sample_dir, sample, cj)
    purity = _purity(sample_dir, sample, cj)
    facts = _facts(variants, cnv, baf, purity)

    _rules_str = str(rules_path if rules_path is not None else (RULES_PATH or ""))
    rules, err = load_rules(_rules_str or None)
    interpretation, rule_errors = interpret(rules, facts)
    if err:
        rule_errors.insert(0, err)

    return {
        "gene": GENE, "arm": ARM,
        "variants": variants,
        "n_variants": len(variants),
        "n_variants_pass": facts["n_variants_pass"],
        "cnv": cnv, "cnv_rows": cnv_rows,
        "baf": baf,
        "purity": purity,
        "facts": facts,
        "observations": _observations(variants, cnv, baf, purity),
        "interpretation": interpretation,
        "rules": {"path": _rules_str, "name": (Path(_rules_str).name if _rules_str else ""),
                  "n": len(rules), "errors": rule_errors},
        "summary_line": " ".join(_observations(variants, cnv, baf, purity)),
    }
