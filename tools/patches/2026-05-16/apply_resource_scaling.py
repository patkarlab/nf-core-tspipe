#!/usr/bin/env python3
"""
Resource scaling for gandalf -- first iteration (revised).

Two files patched in one atomic operation. Sizing chosen to take
near-full advantage of gandalf's 192-core / 1.5 TB capacity while
leaving ~17% headroom for OS, IDE/Jupyter, and any other work.

1. conf/gandalf.config -- bumps the executor envelope and per-process
   ceilings.

2. conf/base.config -- bumps the process_medium and process_high label
   tiers so per-task cpu/memory allocations are larger on first attempt.
   This is what reduces single-sample wall time (the executor envelope
   only helps batch throughput).

Allocation behavior after this patch:
  process_low     attempt 1:   2 cpus,   8 GB
  process_medium  attempt 1:  24 cpus,  96 GB
  process_medium  attempt 2:  48 cpus, 192 GB
  process_high    attempt 1:  64 cpus, 256 GB
  process_high    attempt 2:  96 cpus, 512 GB  (cpus capped, memory at ceiling)
  process_high    attempt 3:  96 cpus, 512 GB  (both dimensions capped)
"""
import shutil
import sys
from pathlib import Path
from datetime import datetime

# pathlib's Path objects represent filesystem paths and have methods
# like .exists(), .read_text(), .with_name(). It's the modern Python
# replacement for the older os.path string-based functions.
TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# A dict mapping each target file to a list of (old_str, new_str) tuples.
# Each replacement is applied exactly once per file. If any old_str is
# missing or appears more than once, the script aborts before touching
# any disk -- this guarantees we cannot leave files half-patched.
PATCHES = {
    Path("conf/gandalf.config"): [
        # ----- per-process ceilings (params.max_*) -----
        (
            "    // Resource ceilings (gandalf has 16+ cores)\n"
            "    max_memory         = '128.GB'\n"
            "    max_cpus           = 16\n"
            "    max_time           = '48.h'",
            "    // Resource ceilings (gandalf has 192 cores / 1.5 TB RAM).\n"
            "    // Bumped 2026-05-16 for batch capacity. base.config's check_max()\n"
            "    // clamps requested resources at these per-process ceilings.\n"
            "    // max_cpus=96 lets process_high retries scale beyond their\n"
            "    // attempt-1 allocation (64 cpus) while preventing any single\n"
            "    // task from consuming more than 60% of executor.cpus.\n"
            "    max_memory         = '512.GB'\n"
            "    max_cpus           = 96\n"
            "    max_time           = '48.h'",
        ),
        # ----- executor budget (total concurrent across all tasks) -----
        (
            "// Limit concurrent processes so we don't exhaust gandalf during a test.\n"
            "// Bump this once you're confident in the configuration.\n"
            "executor {\n"
            "    name           = 'local'\n"
            "    cpus           = 16\n"
            "    memory         = '64 GB'\n"
            "    queueSize      = 8\n"
            "}",
            "// Resource envelope tuned 2026-05-16 for batch capacity (host: 192 cores / 1.5 TB).\n"
            "// Previous: cpus=16, memory='64 GB', queueSize=8.\n"
            "// Targets ~17% headroom -- leaves ~32 cores and ~256 GB for OS and other work.\n"
            "executor {\n"
            "    name           = 'local'\n"
            "    cpus           = 160\n"
            "    memory         = '1280 GB'\n"
            "    queueSize      = 32\n"
            "}",
        ),
    ],
    Path("conf/base.config"): [
        # ----- process_medium: 8/32GB -> 24/96GB -----
        (
            "    withLabel: process_medium {\n"
            "        cpus   = { check_max( 8     * task.attempt, 'cpus'   ) }\n"
            "        memory = { check_max( 32.GB * task.attempt, 'memory' ) }\n"
            "        time   = { check_max( 8.h   * task.attempt, 'time'   ) }\n"
            "    }",
            "    withLabel: process_medium {\n"
            "        cpus   = { check_max( 24    * task.attempt, 'cpus'   ) }\n"
            "        memory = { check_max( 96.GB * task.attempt, 'memory' ) }\n"
            "        time   = { check_max( 8.h   * task.attempt, 'time'   ) }\n"
            "    }",
        ),
        # ----- process_high: 16/64GB -> 64/256GB -----
        (
            "    withLabel: process_high {\n"
            "        cpus   = { check_max( 16    * task.attempt, 'cpus'   ) }\n"
            "        memory = { check_max( 64.GB * task.attempt, 'memory' ) }\n"
            "        time   = { check_max( 16.h  * task.attempt, 'time'   ) }\n"
            "    }",
            "    withLabel: process_high {\n"
            "        cpus   = { check_max( 64    * task.attempt, 'cpus'   ) }\n"
            "        memory = { check_max( 256.GB * task.attempt, 'memory' ) }\n"
            "        time   = { check_max( 16.h  * task.attempt, 'time'   ) }\n"
            "    }",
        ),
    ],
}


def main():
    # === Pre-flight: validate every replacement in every file BEFORE
    # touching disk. The .count() method returns how many times old_str
    # appears; we require exactly 1. If any file fails validation, we
    # exit before modifying anything, so partial application is impossible.
    print("=== Pre-flight validation ===")
    for path, replacements in PATCHES.items():
        if not path.exists():
            sys.exit(f"FATAL: {path} not found. Run from nf-core-tspipe repo root.")
        text = path.read_text()
        for i, (old, _new) in enumerate(replacements, 1):
            count = text.count(old)
            if count == 0:
                sys.exit(f"FATAL: {path} replacement {i}: old_str not found")
            if count > 1:
                sys.exit(f"FATAL: {path} replacement {i}: old_str matched {count} times")
        print(f"  {path}: {len(replacements)} replacement(s) validated")
    print()

    # === Apply: for each file, copy it to a timestamped backup,
    # run the replacements in sequence, write the result back.
    # shutil.copy2 preserves file metadata (timestamps, permissions).
    for path, replacements in PATCHES.items():
        backup = path.with_name(f"{path.name}.bak_resource_scaling_{TS}")
        shutil.copy2(path, backup)
        print(f"=== {path} ===")
        print(f"Backup: {backup}")

        text = path.read_text()
        for i, (old, new) in enumerate(replacements, 1):
            text = text.replace(old, new)
            print(f"  replacement {i}: applied")
        path.write_text(text)
        print(f"  written: {path}")
        print()

    print("Done. Verify with:")
    for path in PATCHES:
        print(f"  git diff {path}")


if __name__ == "__main__":
    main()
