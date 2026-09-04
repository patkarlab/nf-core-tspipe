#!/usr/bin/env python3
"""
tools/patches/2026-09-04/patch_vv_serial_default.py

Promote the VARIANT_VALIDATOR serial override (/tmp/vv_serial.config,
validated on realign_v4: 24 samples, 3 transient failures recovered by
retry) to the repository default in conf/modules.config.

Replaces the MARKER vv_maxforks block (maxForks = 2) with maxForks = 1,
errorStrategy = 'retry', maxRetries = 3, and rewrites the block comment
to reflect the public REST endpoint rather than the retired local stack.

Dry-run by default; --apply writes with a timestamped backup.
Idempotent: a second run reports [skip].
Python 3.6-safe.
"""
import argparse
import datetime
import os
import shutil
import sys

TARGET = "conf/modules.config"
TAG = "vvserial"
MARKER_NEW = "MARKER vv_maxforks_serial"

OLD_BLOCK = (
    "    // MARKER vv_maxforks: the VV REST stack is one gunicorn worker (5 threads);\n"
    "    // 23 parallel samples hung it on 2026-09-02. Two at a time is enough.\n"
    "    withName: 'VARIANT_VALIDATOR' {\n"
    "        maxForks = 2\n"
    "    }\n"
)

NEW_BLOCK = (
    "    // MARKER vv_maxforks_serial: VARIANT_VALIDATOR is serialised. The public\n"
    "    // REST endpoint (params.vv_url) answers one request at a time in practice;\n"
    "    // realign_v4 (24 samples, 2026-09-03) ran clean at maxForks 1 with three\n"
    "    // transient failures recovered by retry. Promoted from the run-specific\n"
    "    // /tmp/vv_serial.config on 2026-09-04.\n"
    "    withName: 'VARIANT_VALIDATOR' {\n"
    "        maxForks      = 1\n"
    "        errorStrategy = 'retry'\n"
    "        maxRetries    = 3\n"
    "    }\n"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="write changes (default: dry-run)")
    parser.add_argument("--repo", default=".",
                        help="repository root (default: current directory)")
    args = parser.parse_args()

    path = os.path.join(args.repo, TARGET)
    if not os.path.isfile(path):
        print("[error] not found: {}".format(path))
        return 1

    with open(path, "r") as fh:
        text = fh.read()

    if MARKER_NEW in text:
        print("[skip] {} already patched ({} present)".format(TARGET, MARKER_NEW))
        return 0

    count = text.count(OLD_BLOCK)
    if count != 1:
        print("[error] anchor block found {} time(s) in {} (expected exactly 1); "
              "read the file from disk and update OLD_BLOCK".format(count, TARGET))
        return 1

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)

    if not args.apply:
        print("[dry-run] would patch {}: maxForks 2 -> 1, add errorStrategy retry, maxRetries 3".format(TARGET))
        print("[dry-run] re-run with --apply to write")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{}.bak_{}_{}".format(path, TAG, stamp)
    shutil.copy2(path, backup)
    print("[backup] {}".format(backup))

    with open(path, "w") as fh:
        fh.write(new_text)
    print("[patch] {}: VARIANT_VALIDATOR maxForks=1, errorStrategy=retry, maxRetries=3".format(TARGET))
    return 0


if __name__ == "__main__":
    sys.exit(main())
