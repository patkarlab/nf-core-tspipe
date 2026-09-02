#!/usr/bin/env python3
"""17_variant_validator.py: raise the startup connectivity probe timeout
from 30 s to 150 s.

Root cause (Female16 pilot, 2026-09-02): VARIANT_VALIDATOR failed with
three probe timeouts although the VV stack was up and serving. Measured
validation latency was 79.7 s and 78.1 s on consecutive calls -- chronic,
not cold-start -- against a 30 s probe. The per-request path already
allows --timeout 120. Latency itself is a separate stack investigation
(see docs/sops/vv_troubleshooting.md); this patch stops a healthy but
slow stack from failing the pipeline at startup.

Dry-run by default; --apply to write. Idempotent via MARKER.
"""
import argparse
import shutil
import sys
import time

TARGET = "bin/17_variant_validator.py"
MARKER = "MARKER: vv_probe_timeout"
TAG = "vv_probe_timeout"
ANCHOR = "resp = requests.get(test_url, timeout=30)"
REPLACEMENT = ("resp = requests.get(test_url, timeout=150)"
               "  # MARKER: vv_probe_timeout -- measured ~80 s per validation")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    ap.add_argument("--target", default=TARGET)
    args = ap.parse_args()
    with open(args.target) as fh:
        src = fh.read()
    if MARKER in src:
        print("[skip] marker present; already patched: %s" % args.target)
        return 0
    n = src.count(ANCHOR)
    if n != 1:
        print("[error] anchor found %d times in %s (expected 1)" % (n, args.target))
        return 1
    if not args.apply:
        print("[dry-run] anchor found, unique. Re-run with --apply.")
        return 0
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = "%s.bak_%s_%s" % (args.target, TAG, ts)
    shutil.copy2(args.target, bak)
    print("[backup] %s" % bak)
    with open(args.target, "w") as fh:
        fh.write(src.replace(ANCHOR, REPLACEMENT))
    print("[patch] applied to %s" % args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
