#!/usr/bin/env python3
"""
test_pindel_gt_filter.py  --  2026-05-19

Standalone contract test for parse_pindel() in bin/flt3_consensus.py
after the GT-filter patch is applied.

Tests the genotype-based contract introduced by
apply_pindel_gt_filter.py:

  (1) No record returned by parse_pindel may correspond to an input
      VCF line whose FORMAT/GT is in the block-list
      ("0/0", "0|0", "./.").
  (2) Positive control: chr13:28034132 (the known FLT3-ITD lead
      record at GT=0/1 in /tmp/d1_pindel_real.vcf) must be present
      in the returned records.

No assertion on VAF, ITD length, supporting reads, or absolute
record count. Those are caller- and panel-specific; locking them
into a test would couple the test to upstream variability and
would also imply numeric thresholds that this project deliberately
does not impose on FLT3-ITD detection.

Expected behaviour:
  - Pre-patch: contract (1) fails (records with bad GT leak through).
  - Post-patch: both contracts pass.

Usage:
  python test_pindel_gt_filter.py
  python test_pindel_gt_filter.py --vcf /tmp/d1_pindel_real.vcf \
      --repo /goast/hemat_data/nf-core-tspipe

Audit memo: docs/audit/2026-05-19/d1d2_real_data_findings.md
"""
import argparse
import sys
from pathlib import Path

REPO_DEFAULT = Path("/goast/hemat_data/nf-core-tspipe")
VCF_DEFAULT = Path("/tmp/d1_pindel_real.vcf")
BAD_GT = ("0/0", "0|0", "./.")
EXPECTED_POS = 28034132


def gt_by_position(vcf):
    """Return {pos: gt} for every non-header record in the VCF.
    All records in the FLT3-filtered Pindel VCF are on chr13; for
    contract checking against parse_pindel output (which exposes
    pos_hg38 but not chrom), position-keyed lookup is sufficient."""
    out = {}
    with open(vcf) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 10:
                continue
            pos = int(parts[1])
            fmt_keys = parts[8].split(":")
            sample_vals = parts[9].split(":")
            fmt = dict(zip(fmt_keys, sample_vals))
            out[pos] = fmt.get("GT", "")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--repo", type=Path, default=REPO_DEFAULT,
                    help="nf-core-tspipe repo root")
    ap.add_argument("--vcf", type=Path, default=VCF_DEFAULT,
                    help="filtered Pindel VCF used as fixture")
    args = ap.parse_args()

    if not args.vcf.exists():
        sys.exit("missing test VCF: {}".format(args.vcf))
    script = args.repo / "bin" / "flt3_consensus.py"
    if not script.exists():
        sys.exit("missing: {}".format(script))

    sys.path.insert(0, str(args.repo / "bin"))
    from flt3_consensus import parse_pindel

    gt_map = gt_by_position(args.vcf)
    n_total = len(gt_map)
    n_bad = sum(1 for g in gt_map.values() if g in BAD_GT)
    n_good = n_total - n_bad
    print("[input]  {}: {} records ({} with GT in {}, {} otherwise)"
          .format(args.vcf.name, n_total, n_bad, list(BAD_GT), n_good))

    records = parse_pindel(args.vcf)
    print("[output] parse_pindel returned {} records".format(len(records)))

    failures = 0

    # Contract 1: no bad-GT record may survive parse_pindel.
    leaked = []
    for r in records:
        pos = r["pos_hg38"]
        gt = gt_map.get(pos, "<missing-in-vcf>")
        if gt in BAD_GT:
            leaked.append((pos, gt))
    if leaked:
        print("[FAIL]   contract 1: {} record(s) with bad GT leaked through"
              .format(len(leaked)))
        for pos, gt in leaked[:5]:
            print("           pos={} gt={}".format(pos, gt))
        if len(leaked) > 5:
            print("           ... ({} more)".format(len(leaked) - 5))
        failures += 1
    else:
        print("[ok]     contract 1: no returned record has GT in the "
              "block-list")

    # Contract 2: known positive control must survive.
    positions = {r["pos_hg38"] for r in records}
    if EXPECTED_POS not in positions:
        print("[FAIL]   contract 2: positive control at pos {} is "
              "absent from output".format(EXPECTED_POS))
        failures += 1
    else:
        print("[ok]     contract 2: positive control at pos {} present"
              .format(EXPECTED_POS))

    if failures:
        print("[FAIL]   {} contract check(s) failed".format(failures))
        sys.exit(1)
    print("[PASS]   all contract checks passed")


if __name__ == "__main__":
    main()
