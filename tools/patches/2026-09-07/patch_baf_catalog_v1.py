#!/usr/bin/env python3
"""
patch_baf_catalog_v1.py -- genome-wide BAF site catalog in BUILD_PON_TWIST
(MARKER BAF_CATALOG_V1). Handoff item 9 (BAF_V2), catalog half.

Edits to workflows/build_pon_twist.nf (all-or-nothing):
  1. params: pon_het_min_samples 3, pon_het_min_depth 50, pon_het_af_lo 0.20,
     pon_het_af_hi 0.80, pon_het_mapq 20; pon_baf_cohort default -> 'all'
     (genome-wide background over all rows with the per-site depth filter;
     chrX informative sites come from the females)
  2. includes BPT_DISCOVER_HETS, BPT_MERGE_HET_SITES
  3. the asset catalog becomes ch_snp_bed_base; BPT_DISCOVER_HETS runs on
     every sample; BPT_MERGE_HET_SITES builds ch_snp_bed, which the existing
     BPT_GATK_COLLECT_ALLELIC_COUNTS and BPT_AGGREGATE_BAF consume unchanged

Dry run by default; --apply writes a .bak_baf_catalog_<ts> backup.
"""

import argparse
import datetime
import re
import shutil
import sys

MARKER = "MARKER BAF_CATALOG_V1"
TARGET = "workflows/build_pon_twist.nf"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


PARAMS = '''// %s: genome-wide BAF site catalog discovered from the normals
// (het in >= pon_het_min_samples include_in_pon rows at >= pon_het_min_depth;
// chrX from females only; PARALOG_LIMITED exons excluded), appended to the
// 17p probe windows. Changing these re-runs discovery merge, allelic counts
// and the BAF aggregation under -resume.
params.pon_het_min_samples = 3
params.pon_het_min_depth   = 50
params.pon_het_af_lo       = 0.20
params.pon_het_af_hi       = 0.80
params.pon_het_mapq        = 20
''' % MARKER

BLOCK = '''
{i}// BAF_CATALOG_V1: het discovery on every row, catalog merge, then the
{i}// existing allelic counting and aggregation run over the merged catalog.
{i}def paralog_tsv = "${{params.pon_assets}}/paralog_limited_exons.tsv"
{i}ch_paralog_exons = file(paralog_tsv).exists() ? Channel.value(file(paralog_tsv)) : Channel.value([])
{i}BPT_DISCOVER_HETS( ch_samples, ch_bed, ch_fasta, ch_fai )
{i}BPT_MERGE_HET_SITES(
{i}    BPT_DISCOVER_HETS.out.hets.map {{ meta, tsv -> tsv }}.collect(),
{i}    ch_sheet,
{i}    ch_snp_bed_base,
{i}    ch_paralog_exons
{i})
{i}ch_snp_bed = BPT_MERGE_HET_SITES.out.bed.first()

'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    t = open(args.target).read()
    if MARKER in t:
        print("[skip] %s already present" % MARKER); sys.exit(0)
    notes = []
    try:
        t, n = sub_once(t, r"^params\.pon_baf_cohort\s*=\s*'male'[^\n]*$",
                        "params.pon_baf_cohort    = 'all'            // BAF_CATALOG_V1: genome-wide background over all rows (per-site depth filter); was 'male'",
                        "pon_baf_cohort -> all"); notes.append(n)
        t, n = sub_once(t, r"^params\.pon_baf_min_het\s*=\s*3[^\n]*\n", lambda m: m.group(0) + PARAMS, "het catalog params"); notes.append(n)
        t, n = sub_once(t, r"^include \{ BPT_AGGREGATE_BAF\s*\} from '\.\./modules/local/bpt_aggregate_baf'[^\n]*$",
                        lambda m: m.group(0) + "\ninclude { BPT_DISCOVER_HETS         } from '../modules/local/bpt_discover_hets'      // BAF_CATALOG_V1\ninclude { BPT_MERGE_HET_SITES       } from '../modules/local/bpt_merge_het_sites'",
                        "includes"); notes.append(n)
        t, n = sub_once(t, r'^(?P<i>[ \t]*)ch_snp_bed\s*=\s*Channel\.value\(file\("\$\{params\.pon_assets\}/snp_sites\.baf\.bed",\s*checkIfExists: true\)\)[^\n]*$',
                        lambda m: '%sch_snp_bed_base = Channel.value(file("${params.pon_assets}/snp_sites.baf.bed", checkIfExists: true))   // BAF_CATALOG_V1: 17p probe windows; ch_snp_bed is built below' % m.group("i"),
                        "asset catalog -> ch_snp_bed_base"); notes.append(n)
        t, n = sub_once(t, r"^(?P<i>[ \t]*)// ---- global prep \(stratum-independent\) -+[ \t]*$",
                        lambda m: BLOCK.format(i=m.group("i")) + m.group(0), "discovery + merge before global prep"); notes.append(n)
    except ValueError as exc:
        print("[error] %s; nothing written" % exc); sys.exit(1)
    for n in notes:
        print(n)
    b0, b1 = open(args.target).read().count("{") - open(args.target).read().count("}"), t.count("{") - t.count("}")
    print("[check] markers %d (expected 1); brace balance %d/%d; ch_snp_bed uses after merge: %d" % (t.count(MARKER), b0, b1, len(re.findall(r"ch_snp_bed\b(?!_base)", t.split("ch_snp_bed = BPT_MERGE_HET_SITES")[1])) if "ch_snp_bed = BPT_MERGE_HET_SITES" in t else -1))
    if t.count(MARKER) != 1 or b0 != b1:
        print("[error] verification failed; nothing written"); sys.exit(1)
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply"); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_baf_catalog_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    open(args.target, "w").write(t)
    print("[backup] %s\n[patch] wrote %s" % (backup, args.target))


if __name__ == "__main__":
    main()
