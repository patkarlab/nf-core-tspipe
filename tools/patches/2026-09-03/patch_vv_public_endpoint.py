#!/usr/bin/env python3
"""VariantValidator: public REST endpoint, response cache, version columns.

Decision 2026-09-03: the local Docker VV stack (one serial gunicorn worker,
~80 s per validation, four SOP procedures) is replaced as the default by
https://rest.variantvalidator.org (measured 1.4 s cold / 0.6 s warm from
gandalf). Changes, all additive:

  bin/17_variant_validator.py
    - --cache-dir: per-variant JSON cache keyed on build, query and VV
      version; consulted before any request, written after each success.
    - VV_Version / VVTA_Version columns from the response metadata, so a
      report can say which VariantValidator release validated it.
    - Probe learns the version; Docker recovery hints only for localhost.
    - Probe timeout message reports the real timeout (was hard-coded 30s).
  modules/local/variant_validator.nf
    - --vv-url ${params.vv_url}; --cache-dir when params.vv_cache_dir set.
  nextflow.config
    - params.vv_url (default public endpoint), params.vv_cache_dir (null).
  conf/gandalf.config
    - vv_cache_dir under the pipeline references root.
  launch_tspipe.sh
    - Docker preflight and recovery only when VV_URL is localhost.

Dry-run by default; --apply writes with timestamped backups. Idempotent
via MARKER. Python 3.6 compatible.
"""
import argparse
import shutil
import sys
import time

MARKER = "MARKER vv_public"
TAG = "vv_public"

EDITS = [
    # ---------------- bin/17_variant_validator.py ----------------
    ("bin/17_variant_validator.py", [
        ('import re\n', 'import json\nimport re\n'),
        ('DEFAULT_VV_URL = "http://localhost:5001"\n',
         'DEFAULT_VV_URL = "http://localhost:5001"\n'
         'PROBE_TIMEOUT = 150   # MARKER vv_public: measured ~80 s per validation on the local stack\n'
         'VV_VERSION = ""       # learned from the probe response metadata\n'
         'VVTA_VERSION = ""\n'),
        ('    parser.add_argument("--timeout", type=int, default=120,\n',
         '    parser.add_argument("--cache-dir", default=None,\n'
         '                        help="Directory for per-variant response cache (keyed on build, "\n'
         '                             "query and VV version); omit to disable caching")\n'
         '    parser.add_argument("--timeout", type=int, default=120,\n'),
        ('            resp = requests.get(test_url, timeout=150)  # MARKER: vv_probe_timeout -- measured ~80 s per validation\n'
         '            if resp.status_code == 200:\n'
         '                data = resp.json()\n'
         '                if data.get("flag") in ("gene_variant", "warning"):\n',
         '            resp = requests.get(test_url, timeout=PROBE_TIMEOUT)  # MARKER: vv_probe_timeout -- measured ~80 s per validation\n'
         '            if resp.status_code == 200:\n'
         '                data = resp.json()\n'
         '                if data.get("flag") in ("gene_variant", "warning"):\n'
         '                    _learn_versions(data)\n'),
        ('            last_error = "request timeout (30s)"\n',
         '            last_error = "request timeout (%ds)" % PROBE_TIMEOUT\n'),
        ('    log.error(\n'
         '        f"Cannot connect to VariantValidator at {base_url} "\n'
         '        f"after {max_attempts} attempts. Last error: {last_error}\\n"\n'
         '        f"  Is the Docker container running?\\n"\n',
         '    if "localhost" not in base_url and "127.0.0.1" not in base_url:\n'
         '        log.error(f"Cannot connect to VariantValidator at {base_url} "\n'
         '                  f"after {max_attempts} attempts. Last error: {last_error}")\n'
         '        return False\n'
         '    log.error(\n'
         '        f"Cannot connect to VariantValidator at {base_url} "\n'
         '        f"after {max_attempts} attempts. Last error: {last_error}\\n"\n'
         '        f"  Is the Docker container running?\\n"\n'),
        ('def build_query_hgvs(hgvsc, mane_select="", hgvsg=""):\n',
         'def _learn_versions(data):\n'
         '    """Record VariantValidator and VVTA versions from a response (MARKER vv_public)."""\n'
         '    global VV_VERSION, VVTA_VERSION\n'
         '    meta = data.get("metadata", {}) if isinstance(data, dict) else {}\n'
         '    VV_VERSION = str(meta.get("variantvalidator_version", VV_VERSION) or VV_VERSION)\n'
         '    VVTA_VERSION = str(meta.get("variantvalidator_hgvs_version", "")\n'
         '                       or meta.get("vvta_version", VVTA_VERSION) or VVTA_VERSION)\n'
         '\n'
         '\n'
         'def _cache_path(cache_dir, hgvsc):\n'
         '    """Cache file for a query: <cache_dir>/<VV version>/<sha1 of build|query>.json."""\n'
         '    import hashlib\n'
         '    if not cache_dir:\n'
         '        return None\n'
         '    key = hashlib.sha1(("%s|%s|all" % (GENOME_BUILD, hgvsc)).encode("utf-8")).hexdigest()\n'
         '    sub = os.path.join(cache_dir, VV_VERSION or "unversioned")\n'
         '    return os.path.join(sub, key + ".json")\n'
         '\n'
         '\n'
         'def build_query_hgvs(hgvsc, mane_select="", hgvsg=""):\n'),
        ('def query_variant(hgvsc, base_url, timeout):\n',
         'def query_variant(hgvsc, base_url, timeout, cache_dir=None):\n'),
        ('        "VV_Valid": False,\n'
         '        "VV_Warnings": "",\n'
         '    }\n'
         '\n'
         '    # URL-encode the variant description\n',
         '        "VV_Valid": False,\n'
         '        "VV_Warnings": "",\n'
         '        "VV_Version": VV_VERSION,\n'
         '        "VVTA_Version": VVTA_VERSION,\n'
         '        "VV_Cached": False,\n'
         '    }\n'
         '\n'
         '    # Cache lookup (MARKER vv_public)\n'
         '    cpath = _cache_path(cache_dir, hgvsc)\n'
         '    data = None\n'
         '    if cpath and os.path.isfile(cpath):\n'
         '        try:\n'
         '            with open(cpath) as fh:\n'
         '                data = json.load(fh)\n'
         '            result["VV_Cached"] = True\n'
         '        except (ValueError, OSError):\n'
         '            data = None\n'
         '\n'
         '    # URL-encode the variant description\n'),
        ('    max_retries = 5\n'
         '    for attempt in range(max_retries):\n'
         '        try:\n'
         '            resp = requests.get(url, timeout=timeout)\n',
         '    max_retries = 5 if data is None else 0\n'
         '    for attempt in range(max_retries):\n'
         '        try:\n'
         '            resp = requests.get(url, timeout=timeout)\n'),
        ('            resp.raise_for_status()\n'
         '            data = resp.json()\n'
         '            break\n',
         '            resp.raise_for_status()\n'
         '            data = resp.json()\n'
         '            _learn_versions(data)\n'
         '            result["VV_Version"] = VV_VERSION\n'
         '            result["VVTA_Version"] = VVTA_VERSION\n'
         '            if cpath:\n'
         '                try:\n'
         '                    os.makedirs(os.path.dirname(cpath), exist_ok=True)\n'
         '                    tmp = cpath + ".tmp.%d" % os.getpid()\n'
         '                    with open(tmp, "w") as fh:\n'
         '                        json.dump(data, fh)\n'
         '                    os.replace(tmp, cpath)\n'
         '                except OSError:\n'
         '                    pass\n'
         '            break\n'),
        ('    else:\n'
         '        result["VV_Warnings"] = "API_ERROR: max retries exceeded (rate limited)"\n'
         '        return result\n',
         '    else:\n'
         '        if data is None:\n'
         '            result["VV_Warnings"] = "API_ERROR: max retries exceeded (rate limited)"\n'
         '            return result\n'),
        ('def validate_variants(df, base_url, threads, timeout):\n',
         'def validate_variants(df, base_url, threads, timeout, cache_dir=None):\n'),
        ('    for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings"]:\n'
         '        df[col] = ""\n'
         '    df["VV_Valid"] = ""\n',
         '    for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings",\n'
         '                "VV_Version", "VVTA_Version"]:\n'
         '        df[col] = ""\n'
         '    df["VV_Valid"] = ""\n'
         '    df["VV_Cached"] = pd.Series([""] * len(df), index=df.index, dtype=object)\n'),
        ('            executor.submit(query_variant, hgvsc, base_url, timeout): hgvsc\n',
         '            executor.submit(query_variant, hgvsc, base_url, timeout, cache_dir): hgvsc\n'),
        ('            for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings"]:\n'
         '                df.at[idx, col] = result.get(col, "")\n'
         '            df.at[idx, "VV_Valid"] = result.get("VV_Valid", False)\n',
         '            for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings",\n'
         '                        "VV_Version", "VVTA_Version"]:\n'
         '                df.at[idx, col] = result.get(col, "")\n'
         '            df.at[idx, "VV_Valid"] = result.get("VV_Valid", False)\n'
         '            df.at[idx, "VV_Cached"] = result.get("VV_Cached", False)\n'),
        ('    df, total_queried, unique_queried, total_failed = validate_variants(\n'
         '        df, args.vv_url, args.threads, args.timeout\n'
         '    )\n',
         '    df, total_queried, unique_queried, total_failed = validate_variants(\n'
         '        df, args.vv_url, args.threads, args.timeout, args.cache_dir\n'
         '    )\n'),
        ('        "VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Transcript", "VV_Valid", "VV_Warnings",\n'
         '        "OncoVI_Score",',
         '        "VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Transcript", "VV_Valid", "VV_Warnings",\n'
         '        "VV_Version", "VVTA_Version", "VV_Cached",\n'
         '        "OncoVI_Score",'),
        ('    log.info(f"  Failed:                   {total_failed}")\n',
         '    log.info(f"  Failed:                   {total_failed}")\n'
         '    cached = (df["VV_Cached"] == True).sum() + (df["VV_Cached"] == "True").sum()  # noqa\n'
         '    log.info(f"  Served from cache:        {cached}")\n'
         '    log.info(f"  VariantValidator:         {VV_VERSION or \'unknown\'} (VVTA {VVTA_VERSION or \'unknown\'})")\n'),
    ]),
    # ---------------- modules/local/variant_validator.nf ----------------
    ("modules/local/variant_validator.nf", [
        ('            --vv-url http://localhost:5001 \\\\\n'
         '            --threads 1 \\\\\n'
         '            --timeout 120\n',
         '            --vv-url ${params.vv_url} \\\\\n'
         '            ${params.vv_cache_dir ? "--cache-dir " + params.vv_cache_dir : ""} \\\\\n'
         '            --threads 1 \\\\\n'
         '            --timeout 120\n'),
        ('            vv_url: http://localhost:5001\n',
         '            vv_url: ${params.vv_url}   # MARKER vv_public\n'),
    ]),
    # ---------------- nextflow.config ----------------
    ("nextflow.config", [
        ("    legacy_root        = '/home/hemat/targeted-seq-pipeline'\n"
         "    legacy_python_env  = '/home/hemat/anaconda3/envs/targeted-seq'\n",
         "    legacy_root        = '/home/hemat/targeted-seq-pipeline'\n"
         "    legacy_python_env  = '/home/hemat/anaconda3/envs/targeted-seq'\n"
         "    // ---- VariantValidator endpoint (MARKER vv_public, 2026-09-03) ----\n"
         "    // Public REST service by default (1-2 s per variant, no local stack).\n"
         "    // Set to http://localhost:5001 to use the Docker stack (see\n"
         "    // docs/sops/vv_troubleshooting.md). vv_cache_dir caches responses per\n"
         "    // VV version; null disables the cache.\n"
         "    vv_url             = 'https://rest.variantvalidator.org'\n"
         "    vv_cache_dir       = null\n"),
    ]),
    # ---------------- conf/gandalf.config ----------------
    ("conf/gandalf.config", [
        ('    // FLT3 ensemble: container runtime (\'docker\' or \'singularity\')\n',
         '    // VariantValidator response cache (MARKER vv_public); shared across runs\n'
         '    vv_cache_dir       = "${params.pipeline_root}/references/vv_cache"\n'
         '\n'
         '    // FLT3 ensemble: container runtime (\'docker\' or \'singularity\')\n'),
    ]),
    # ---------------- launch_tspipe.sh ----------------
    ("launch_tspipe.sh", [
        ('# ---- Preflight ----\n'
         'log "VV preflight: probing $VV_URL"\n'
         'if vv_health_check ; then\n',
         '# ---- Preflight ----\n'
         '# MARKER vv_public: Docker recovery only makes sense for the local stack.\n'
         'if [[ "$VV_URL" != *localhost* && "$VV_URL" != *127.0.0.1* ]]; then\n'
         '    log "VV preflight: probing remote endpoint $VV_URL"\n'
         '    if vv_health_check ; then\n'
         '        log "VV preflight: OK (HTTP 200)"\n'
         '    else\n'
         '        err "VV preflight: remote endpoint $VV_URL not reachable; check egress or set VV_URL to the local stack."\n'
         '        exit 10\n'
         '    fi\n'
         'elif vv_health_check ; then\n'
         '    log "VV preflight: probing $VV_URL"\n'),
    ]),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    import os
    ts = time.strftime("%Y%m%d_%H%M%S")
    rc = 0
    for rel, edits in EDITS:
        path = os.path.join(args.root, rel)
        if not os.path.isfile(path):
            print("[error] missing:", path); rc = 1; continue
        s = open(path).read()
        if MARKER in s:
            print("[skip] already patched:", rel); continue
        ok = True
        for old, new in edits:
            n = s.count(old)
            if n != 1:
                print("[error] %s: anchor found %d times: %r" % (rel, n, old[:60])); ok = False
        if not ok:
            rc = 1; continue
        for old, new in edits:
            s = s.replace(old, new)
        if not args.apply:
            print("[dry-run] %s: %d edits ready" % (rel, len(edits))); continue
        bak = "%s.bak_%s_%s" % (path, TAG, ts)
        shutil.copy2(path, bak); print("[backup]", bak)
        open(path, "w").write(s); print("[patch]", rel)
        if rel.endswith(".py"):
            import ast
            ast.parse(s); print("[ok] ast.parse", rel)
    return rc


if __name__ == "__main__":
    sys.exit(main())
