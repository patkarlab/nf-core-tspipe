#!/usr/bin/env python3
"""
17_variant_validator.py -- Validate HGVS nomenclature via VariantValidator.

Input:  results/{sample}/annotation/{sample}.somaticseq.oncovi.tsv (default)
Output: results/{sample}/annotation/{sample}.somaticseq.validated.tsv

For each variant with an HGVSc value, queries the VariantValidator REST API
to validate and correct HGVS nomenclature. Replaces original HGVSc/HGVSp/HGVSg
with validated versions (VV_HGVSc, VV_HGVSp, VV_HGVSg) and adds:
  VV_Transcript     Reference transcript used
  VV_Valid          True/False -- whether validation succeeded
  VV_Warnings       Validation warnings or correction notes
  VV_Exon           Exon number from VV's variant_exonic_positions
  VV_Version, VVTA_Version, VV_Cached

CHANGELOG
  2026-05-22  Added retry-with-exponential-backoff to check_vv_connection().
              New CLI flags: --connect-retries, --connect-backoff.
  2026-09-04  Public endpoint support, per-variant response cache keyed on
              VV version (MARKER vv_public).
  2026-09-06  Rate-limit and query-construction fixes (MARKER vv_v2), from
              the realign_v4_female run (5-6 min per normal, 4 failures each):
              - 429: honour Retry-After, backoff 5/10/20/40/60 s, and a fixed
                pause between live queries (--query-interval, default 1.0 s).
              - 4xx other than 429 are deterministic: no retry, result cached
                as a negative entry so the variant is not re-queried on every
                sample (--no-negative-cache to disable). 5xx retried twice.
              - Non-coding transcript HGVS (n.) is not sent (skipped with a
                reason); the genomic fallback uses the pseudo-VCF form
                chr-pos-ref-alt from Chr/Start/Ref/Alt, which the REST
                endpoint accepts, instead of VEP's chrX:g. string.
              - Queries use the mane_select transcript set instead of /all
                (--select-transcripts to override) and result selection
                prefers VV's own mane_select annotation.
"""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import json
import re

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_VV_URL = "http://localhost:5001"
PROBE_TIMEOUT = 150   # MARKER vv_public: measured ~80 s per validation on the local stack
VV_VERSION = ""       # learned from the probe response metadata
VVTA_VERSION = ""
GENOME_BUILD = "GRCh38"

# Defaults for connection-check retry behavior. Backoffs grow exponentially:
# attempt 1 immediate, then waits of 30s, 60s, 120s before attempts 2/3/4.
DEFAULT_CONNECT_RETRIES = 3
DEFAULT_CONNECT_BACKOFF = 30

# MARKER vv_v2: query pacing and retry policy for the public endpoint
DEFAULT_QUERY_INTERVAL = 1.0            # seconds between live queries (fair use)
DEFAULT_SELECT_TRANSCRIPTS = "mane_select"
RATE_LIMIT_BACKOFF = (5, 10, 20, 40, 60)  # seconds; Retry-After header wins when present
TRANSIENT_RETRIES = 3                   # timeouts / connection errors
TRANSIENT_BACKOFF = (5, 10, 20)
SERVER_ERROR_RETRIES = 2                # HTTP 5xx
SERVER_ERROR_BACKOFF = (10, 20)

_MISSING = ("-1", "", "nan", "None", ".")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate HGVS nomenclature via VariantValidator"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name")
    parser.add_argument("-i", "--input", default=None,
                        help="Input TSV (default: oncovi TSV; use --all for filtered TSV)")
    parser.add_argument("-o", "--outdir", default=None,
                        help="Output directory (default: same as input)")
    parser.add_argument("--all", action="store_true", dest="all_variants",
                        help="Run on all filtered variants instead of oncovi only")
    parser.add_argument("--vv-url", default=DEFAULT_VV_URL,
                        help=f"VariantValidator base URL (default: {DEFAULT_VV_URL})")
    parser.add_argument("--threads", type=int, default=1,
                        help="Number of parallel query threads (default: 1)")
    parser.add_argument("--cache-dir", default=None,
                        help="Directory for per-variant response cache (keyed on build, "
                             "query, transcript set and VV version); omit to disable caching")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-query timeout in seconds (default: 120)")
    parser.add_argument("--query-interval", type=float, default=DEFAULT_QUERY_INTERVAL,
                        help=f"Pause in seconds after each live query (default: {DEFAULT_QUERY_INTERVAL})")
    parser.add_argument("--select-transcripts", default=DEFAULT_SELECT_TRANSCRIPTS,
                        help=f"VV transcript set: mane_select, mane, select, all, or a list "
                             f"(default: {DEFAULT_SELECT_TRANSCRIPTS})")
    parser.add_argument("--no-negative-cache", action="store_true",
                        help="Do not cache deterministic failures (HTTP 4xx)")
    parser.add_argument("--connect-retries", type=int, default=DEFAULT_CONNECT_RETRIES,
                        help=(f"Number of VV connection attempts at startup "
                              f"(default: {DEFAULT_CONNECT_RETRIES})"))
    parser.add_argument("--connect-backoff", type=int, default=DEFAULT_CONNECT_BACKOFF,
                        help=(f"Initial backoff in seconds between connection retries; "
                              f"doubled after each failure (default: {DEFAULT_CONNECT_BACKOFF})"))
    return parser.parse_args()


def check_vv_connection(base_url,
                        max_attempts=DEFAULT_CONNECT_RETRIES,
                        initial_backoff=DEFAULT_CONNECT_BACKOFF):
    """Verify VariantValidator is reachable with a test query.

    Retries with exponential backoff to survive transient VV outages, most
    commonly a gunicorn restart inside the Docker container (30s, 60s, 120s).
    Returns True on the first successful connection, False after all attempts.
    """
    test_url = (f"{base_url}/VariantValidator/variantvalidator/"
                f"GRCh38/NM_000088.4:c.589G>T/all?content-type=application/json")

    last_error = "no attempt made"
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(test_url, timeout=PROBE_TIMEOUT)  # MARKER: vv_probe_timeout
            if resp.status_code == 200:
                data = resp.json()
                if data.get("flag") in ("gene_variant", "warning"):
                    _learn_versions(data)
                    if attempt == 1:
                        log.info(f"VariantValidator reachable at {base_url}")
                    else:
                        log.info(
                            f"VariantValidator reachable at {base_url} "
                            f"(succeeded on attempt {attempt}/{max_attempts})"
                        )
                    return True
                last_error = f"unexpected response flag: {data.get('flag')!r}"
            else:
                last_error = f"HTTP {resp.status_code}"
        except requests.ConnectionError as e:
            last_error = f"connection refused ({e.__class__.__name__})"
        except requests.Timeout:
            last_error = "request timeout (%ds)" % PROBE_TIMEOUT
        except ValueError:
            last_error = "invalid JSON response"
        except Exception as e:
            last_error = f"{e.__class__.__name__}: {e}"

        if attempt < max_attempts:
            wait = initial_backoff * (2 ** (attempt - 1))
            log.warning(
                f"VV connection attempt {attempt}/{max_attempts} failed "
                f"({last_error}); waiting {wait}s before next attempt"
            )
            time.sleep(wait)

    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        log.error(f"Cannot connect to VariantValidator at {base_url} "
                  f"after {max_attempts} attempts. Last error: {last_error}")
        return False
    log.error(
        f"Cannot connect to VariantValidator at {base_url} "
        f"after {max_attempts} attempts. Last error: {last_error}\n"
        f"  Is the Docker container running?\n"
        f"  See docs/sops/vv_troubleshooting.md for the SOP."
    )
    return False


def _learn_versions(data):
    """Record VariantValidator and VVTA versions from a response (MARKER vv_public)."""
    global VV_VERSION, VVTA_VERSION
    meta = data.get("metadata", {}) if isinstance(data, dict) else {}
    VV_VERSION = str(meta.get("variantvalidator_version", VV_VERSION) or VV_VERSION)
    VVTA_VERSION = str(meta.get("variantvalidator_hgvs_version", "")
                       or meta.get("vvta_version", VVTA_VERSION) or VVTA_VERSION)


def _cache_path(cache_dir, query, select):
    """Cache file: <cache_dir>/<VV version>/<sha1 of build|query|select>.json."""
    import hashlib
    if not cache_dir:
        return None
    key = hashlib.sha1(("%s|%s|%s" % (GENOME_BUILD, query, select)).encode("utf-8")).hexdigest()
    sub = os.path.join(cache_dir, VV_VERSION or "unversioned")
    return os.path.join(sub, key + ".json")


def _cache_write(cpath, data):
    if not cpath:
        return
    try:
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        tmp = cpath + ".tmp.%d" % os.getpid()
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, cpath)
    except OSError:
        pass


def build_query_hgvs(hgvsc, mane_select="", hgvsg="", chrom="", pos="", ref="", alt=""):
    """Build the query string for VariantValidator (MARKER vv_v2).

    Returns (query, reason). query is None when the variant is not queried,
    and reason says why. Strategy, in order:
      1. c. change on the MANE Select RefSeq transcript when VEP provides one.
      2. Pseudo-VCF genomic form chr-pos-ref-alt (accepted by the REST
         endpoint; VEP's chrX:g. string is not).
      3. HGVSg if it is already an NC_ accession form.
    Non-coding transcript HGVS (n.) is never sent: VV cannot validate it
    against the coding transcript set and the query fails deterministically.
    """
    hgvsc = str(hgvsc).strip()
    mane = str(mane_select).strip()
    hgvsg = str(hgvsg).strip()
    chrom = str(chrom).strip()
    pos = str(pos).strip()
    ref = str(ref).strip().upper()
    alt = str(alt).strip().upper()

    if hgvsc in _MISSING:
        return None, "no_hgvsc"

    match = re.search(r':([cn])\.(.+)$', hgvsc)
    if match and match.group(1) == "n":
        return None, "noncoding_transcript"
    if match and mane not in _MISSING:
        return f"{mane}:c.{match.group(2)}", "mane_c"

    if (chrom not in _MISSING and pos not in _MISSING
            and re.fullmatch(r"[ACGT]+", ref or "") and re.fullmatch(r"[ACGT]+", alt or "")):
        return f"{chrom}-{pos}-{ref}-{alt}", "pseudo_vcf"

    if hgvsg not in _MISSING and hgvsg.startswith("NC_"):
        return hgvsg, "hgvsg_nc"

    return None, "no_query_form"


def _fetch(url, timeout, query_interval):
    """GET with the vv_v2 retry policy. Returns (data, error_string, deterministic).

    deterministic=True means the failure will recur for this query on this VV
    version (HTTP 4xx other than 429) and may be cached as a negative entry.
    """
    rl = 0
    tr = 0
    se = 0
    while True:
        try:
            resp = requests.get(url, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as e:
            if tr < TRANSIENT_RETRIES:
                time.sleep(TRANSIENT_BACKOFF[min(tr, len(TRANSIENT_BACKOFF) - 1)])
                tr += 1
                continue
            return None, f"API_ERROR: {e.__class__.__name__} after {TRANSIENT_RETRIES} retries", False
        except requests.RequestException as e:
            return None, f"API_ERROR: {e}", False
        finally:
            if query_interval > 0:
                time.sleep(query_interval)

        status = resp.status_code
        if status == 429:
            if rl >= len(RATE_LIMIT_BACKOFF):
                return None, "API_ERROR: rate limited (HTTP 429) after %d backoffs" % rl, False
            wait = RATE_LIMIT_BACKOFF[rl]
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    wait = max(wait, int(float(ra)))
                except ValueError:
                    pass
            log.warning(f"HTTP 429 from VV; waiting {wait}s (backoff {rl + 1}/{len(RATE_LIMIT_BACKOFF)})")
            time.sleep(wait)
            rl += 1
            continue
        if 400 <= status < 500:
            return None, f"API_ERROR: HTTP {status} for {url.split('/variantvalidator/')[-1].split('?')[0]}", True
        if status >= 500:
            if se < SERVER_ERROR_RETRIES:
                time.sleep(SERVER_ERROR_BACKOFF[min(se, len(SERVER_ERROR_BACKOFF) - 1)])
                se += 1
                continue
            return None, f"API_ERROR: HTTP {status} after {SERVER_ERROR_RETRIES} retries", False
        try:
            return resp.json(), "", False
        except ValueError:
            return None, "API_ERROR: invalid JSON response", False


def query_variant(query, base_url, timeout, cache_dir=None, select=DEFAULT_SELECT_TRANSCRIPTS,
                  query_interval=DEFAULT_QUERY_INTERVAL, negative_cache=True):
    """Query VariantValidator for a single variant.

    Returns dict with VV_HGVSc, VV_HGVSp, VV_HGVSg, VV_Exon, VV_Transcript,
    VV_Valid, VV_Warnings, VV_Version, VVTA_Version, VV_Cached.
    """
    result = {
        "VV_HGVSc": "",
        "VV_HGVSp": "",
        "VV_HGVSg": "",
        "VV_Exon": "",
        "VV_Transcript": "",
        "VV_Valid": False,
        "VV_Warnings": "",
        "VV_Version": VV_VERSION,
        "VVTA_Version": VVTA_VERSION,
        "VV_Cached": False,
    }

    # Cache lookup (MARKER vv_public); negative entries carry "_error"
    cpath = _cache_path(cache_dir, query, select)
    data = None
    if cpath and os.path.isfile(cpath):
        try:
            with open(cpath) as fh:
                data = json.load(fh)
            result["VV_Cached"] = True
        except (ValueError, OSError):
            data = None
    if isinstance(data, dict) and "_error" in data:
        result["VV_Warnings"] = "%s (cached)" % data["_error"]
        return result

    if data is None:
        url = (
            f"{base_url}/VariantValidator/variantvalidator/"
            f"{GENOME_BUILD}/{requests.utils.quote(query, safe='')}/{select}"
            f"?content-type=application/json"
        )
        data, err, deterministic = _fetch(url, timeout, query_interval)
        if data is None:
            result["VV_Warnings"] = err
            if deterministic and negative_cache and cpath:
                _cache_write(cpath, {"_error": err, "_query": query, "_select": select})
            return result
        _learn_versions(data)
        result["VV_Version"] = VV_VERSION
        result["VVTA_Version"] = VVTA_VERSION
        _cache_write(cpath, data)

    # Check flag
    flag = data.get("flag", "")

    # Find the variant result keys (not 'flag' or 'metadata')
    variant_keys = [k for k in data.keys() if k not in ("flag", "metadata")]

    # MARKER vv_v2: genes without a MANE Select transcript return no entry for
    # the mane_select set; fall back once to the full transcript set.
    if not variant_keys and select != "all" and flag != "intergenic":
        return query_variant(query, base_url, timeout, cache_dir, "all",
                             query_interval, negative_cache)

    if not variant_keys:
        result["VV_Warnings"] = f"NO_RESULT: flag={flag}"
        return result

    if flag == "intergenic":
        result["VV_Warnings"] = "INTERGENIC: variant maps to intergenic region"
        return result

    warnings = []

    # Result selection (MARKER vv_v2): VV's own MANE Select flag first, then the
    # transcript we asked for (version-insensitive), then the first entry with
    # a transcript-level description.
    input_transcript = query.split(":")[0] if ":" in query else ""
    input_tx_base = input_transcript.split(".")[0]
    candidates = [data[k] for k in variant_keys if isinstance(data[k], dict)]

    best_match = None
    for vdata in candidates:
        ann = vdata.get("annotations", {})
        if isinstance(ann, dict) and ann.get("mane_select") is True and vdata.get("hgvs_transcript_variant"):
            best_match = vdata
            break
    if best_match is None and input_tx_base:
        for vdata in candidates:
            vv_hgvsc = vdata.get("hgvs_transcript_variant", "") or ""
            vv_tx_base = (vv_hgvsc.split(":")[0] if ":" in vv_hgvsc else "").split(".")[0]
            if vv_tx_base and vv_tx_base == input_tx_base:
                best_match = vdata
                break
    if best_match is None:
        for vdata in candidates:
            if vdata.get("hgvs_transcript_variant"):
                best_match = vdata
                break

    if best_match is None:
        for vdata in candidates:
            vw = vdata.get("validation_warnings", [])
            if vw:
                warnings.extend(vw)
        result["VV_Warnings"] = "; ".join(warnings) if warnings else f"NO_MATCH: flag={flag}"
        return result

    vdata = best_match

    vv_hgvsc = vdata.get("hgvs_transcript_variant", "")
    result["VV_HGVSc"] = vv_hgvsc
    result["VV_Transcript"] = vv_hgvsc.split(":")[0] if ":" in vv_hgvsc else ""

    protein = vdata.get("hgvs_predicted_protein_consequence", {})
    if isinstance(protein, dict):
        result["VV_HGVSp"] = protein.get("tlr", "") or protein.get("slr", "")

    pal = vdata.get("primary_assembly_loci", {})
    grch38 = pal.get("grch38", {}) if isinstance(pal, dict) else {}
    result["VV_HGVSg"] = grch38.get("hgvs_genomic_description", "") if isinstance(grch38, dict) else ""

    # Exon number from variant_exonic_positions (keyed by RefSeq chromosome
    # accession; transcript-based numbering is build-independent so any key
    # serves as fallback; intronic variants leave VV_Exon empty).
    exon = ""
    vep = vdata.get("variant_exonic_positions", {})
    if isinstance(vep, dict) and vep:
        acc = result["VV_HGVSg"].split(":")[0] if result["VV_HGVSg"] else ""
        ep = vep.get(acc)
        if ep is None:
            ep = next(iter(vep.values()))
        if isinstance(ep, dict):
            se = str(ep.get("start_exon", "")).strip()
            ee = str(ep.get("end_exon", "")).strip()
            if se and ee:
                exon = se if se == ee else (se + "-" + ee)
            elif se:
                exon = se
    result["VV_Exon"] = exon

    vw = vdata.get("validation_warnings", [])
    if vw:
        warnings.extend(vw)

    # Did VV correct the description we sent (transcript-based queries only)?
    if vv_hgvsc and ":" in query and vv_hgvsc != query:
        input_no_ver = ":".join(p.split(".")[0] if i == 0 else p
                                for i, p in enumerate(query.split(":")))
        vv_no_ver = ":".join(p.split(".")[0] if i == 0 else p
                             for i, p in enumerate(vv_hgvsc.split(":")))
        if input_no_ver != vv_no_ver:
            warnings.insert(0, f"CORRECTED: {query} -> {vv_hgvsc}")
        elif query.split(":")[0] != vv_hgvsc.split(":")[0]:
            warnings.insert(0, f"TRANSCRIPT_VERSION: {query.split(':')[0]} -> {vv_hgvsc.split(':')[0]}")

    result["VV_Valid"] = True
    result["VV_Warnings"] = "; ".join(warnings)
    return result


def validate_variants(df, base_url, threads, timeout, cache_dir=None,
                      select=DEFAULT_SELECT_TRANSCRIPTS, query_interval=DEFAULT_QUERY_INTERVAL,
                      negative_cache=True):
    """Validate all variants with HGVSc values."""
    mask = ~df["HGVSc"].isin(["-1", "", "nan"]) & df["HGVSc"].notna()
    query_indices = df.index[mask].tolist()
    skip_count = len(df) - len(query_indices)
    log.info(f"Querying {len(query_indices)} variants ({skip_count} skipped - no HGVSc)")

    def col(idx, name):
        return str(df.at[idx, name]) if name in df.columns else ""

    query_to_indices = {}
    idx_to_query = {}
    skip_reasons = {}
    form_counts = {}
    for idx in query_indices:
        query, reason = build_query_hgvs(
            col(idx, "HGVSc"), col(idx, "MANE_SELECT"), col(idx, "HGVSg"),
            col(idx, "Chr"), col(idx, "Start"), col(idx, "Ref"), col(idx, "Alt"))
        if query:
            query_to_indices.setdefault(query, []).append(idx)
            idx_to_query[idx] = query
            form_counts[reason] = form_counts.get(reason, 0) + 1
        else:
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    unique_queries = list(query_to_indices.keys())
    log.info(f"Unique query values: {len(unique_queries)} "
             f"(forms: {form_counts}; not queried: {skip_reasons or 0})")

    for c in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings",
              "VV_Version", "VVTA_Version"]:
        df[c] = ""
    df["VV_Valid"] = ""
    df["VV_Cached"] = pd.Series([""] * len(df), index=df.index, dtype=object)

    results = {}
    completed = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_query = {
            executor.submit(query_variant, q, base_url, timeout, cache_dir, select,
                            query_interval, negative_cache): q
            for q in unique_queries
        }
        for future in as_completed(future_to_query):
            q = future_to_query[future]
            completed += 1
            try:
                result = future.result()
            except Exception as e:
                result = {
                    "VV_HGVSc": "", "VV_HGVSp": "", "VV_HGVSg": "",
                    "VV_Exon": "", "VV_Transcript": "", "VV_Valid": False,
                    "VV_Warnings": f"EXCEPTION: {e}", "VV_Cached": False,
                }
            if not result["VV_Valid"]:
                failed += 1
            results[q] = result
            if completed % 50 == 0 or completed == len(unique_queries):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                log.info(f"  Progress: {completed}/{len(unique_queries)} "
                         f"({rate:.2f} variants/sec, {failed} failed)")

    # Apply results; rows that were not queried get a reason in VV_Warnings
    for query, indices in query_to_indices.items():
        result = results.get(query, {})
        for idx in indices:
            for c in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings",
                      "VV_Version", "VVTA_Version"]:
                df.at[idx, c] = result.get(c, "")
            df.at[idx, "VV_Valid"] = result.get("VV_Valid", False)
            df.at[idx, "VV_Cached"] = result.get("VV_Cached", False)
    for idx in query_indices:
        if idx not in idx_to_query:
            _, reason = build_query_hgvs(
                col(idx, "HGVSc"), col(idx, "MANE_SELECT"), col(idx, "HGVSg"),
                col(idx, "Chr"), col(idx, "Start"), col(idx, "Ref"), col(idx, "Alt"))
            df.at[idx, "VV_Warnings"] = f"NOT_QUERIED: {reason}"
            df.at[idx, "VV_Valid"] = False
            df.at[idx, "VV_Cached"] = False

    return df, len(query_indices), len(unique_queries), failed


def main():
    args = parse_args()
    sample = args.sample

    default_annot_dir = os.path.join(PIPELINE_DIR, "results", sample, "annotation")

    if args.input:
        input_tsv = args.input
    else:
        annot_dir = args.outdir or default_annot_dir
        if args.all_variants:
            input_tsv = os.path.join(annot_dir, f"{sample}.somaticseq.filtered.tsv")
        else:
            input_tsv = os.path.join(annot_dir, f"{sample}.somaticseq.oncovi.tsv")

    if not os.path.exists(input_tsv):
        log.error(f"Input file not found: {input_tsv}")
        sys.exit(1)

    outdir = args.outdir or os.path.dirname(input_tsv)
    os.makedirs(outdir, exist_ok=True)

    if not check_vv_connection(args.vv_url,
                               max_attempts=args.connect_retries,
                               initial_backoff=args.connect_backoff):
        sys.exit(1)

    df = pd.read_csv(input_tsv, sep="\t", dtype=str)
    log.info(f"Read {len(df)} variants from {input_tsv}")

    df, total_queried, unique_queried, total_failed = validate_variants(
        df, args.vv_url, args.threads, args.timeout, args.cache_dir,
        args.select_transcripts, args.query_interval, not args.no_negative_cache
    )

    desired_order = [
        "Sample", "Chr", "Start", "End", "Ref", "Alt", "Gene", "Consequence",
        "HGVSc", "HGVSp", "HGVSg",
        "VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Transcript", "VV_Valid", "VV_Warnings",
        "VV_Version", "VVTA_Version", "VV_Cached",
        "OncoVI_Score", "OncoVI_Classification", "OncoVI_Criteria",
        "IMPACT", "VariantCaller_Count", "Callers", "REF_COUNT", "ALT_COUNT",
        "VAF_pct", "SomaticSeq_Verdict", "COSMIC_ID", "ClinVar", "SIFT", "PolyPhen",
        "gnomAD_exome_AF", "gnomAD_genome_AF", "AF_1KG", "Max_AF", "rsID",
        "MANE_SELECT", "Canonical", "Existing_variation", "Dedup_Note", "Filter",
    ]
    final_cols = [c for c in desired_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in desired_order]
    if extra_cols:
        log.info(f"Extra columns appended at end: {extra_cols}")
    df = df[final_cols + extra_cols]

    out_path = os.path.join(outdir, f"{sample}.somaticseq.clinical.validated.tsv")
    df.to_csv(out_path, sep="\t", index=False)
    log.info(f"Wrote validated output: {out_path}")

    total_valid = (df["VV_Valid"] == True).sum() + (df["VV_Valid"] == "True").sum()  # noqa
    total_warnings = df["VV_Warnings"].apply(lambda x: bool(str(x).strip())).sum()
    total_corrected = df["VV_Warnings"].str.contains("CORRECTED", na=False).sum()
    cached = (df["VV_Cached"] == True).sum() + (df["VV_Cached"] == "True").sum()  # noqa

    log.info("=== VariantValidator Summary ===")
    log.info(f"  Total variants in file:   {len(df)}")
    log.info(f"  Queried (with HGVSc):     {total_queried} ({unique_queried} unique)")
    log.info(f"  Successfully validated:   {total_valid}")
    log.info(f"  With warnings:            {total_warnings}")
    log.info(f"  HGVS corrected by VV:     {total_corrected}")
    log.info(f"  Failed:                   {total_failed}")
    log.info(f"  Served from cache:        {cached}")
    log.info(f"  VariantValidator:         {VV_VERSION or 'unknown'} (VVTA {VVTA_VERSION or 'unknown'})")


if __name__ == "__main__":
    main()
