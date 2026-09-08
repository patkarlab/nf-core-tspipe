#!/usr/bin/env python3
"""bin/mnv_merge.py -- MNV_MERGE_V1 (N2)

Add multi-nucleotide variant (MNV) records to the SomaticSeq consensus VCF.

SomaticSeq decomposes every caller MNV into SNVs. Mutect2's MNV support is
lost on the components (MVDKFP M flag = 0) while VarDict's is credited, so a
real somatic dinucleotide can drop a caller and sink to LOW_CALLERS, and VEP
annotates the two SNVs separately (wrong codon-level HGVS). This script
re-joins them BEFORE VEP:

  candidate run  consecutive consensus SNVs on one chromosome whose positions
                 differ by <= MAX_GAP (2: adjacent, or one base between)
  evidence       a Mutect2 raw MNV record covering the run exactly, or a
                 VarDict MNV record covering it exactly, or every SNV of the
                 run present in Mutect2 raw with the same PID and PGT
  merged record  added alongside the components (nothing is removed):
                 REF/ALT span the run (gap bases from the reference),
                 MVDKFP = AND of components with M set when Mutect2 supports
                 the MNV and D set when VarDict does, NUM_TOOLS recomputed,
                 AF/FORMAT from the lowest-AF component, FILTER = worst of
                 the components, INFO MNV_OF and MNV_EVIDENCE
  components     INFO MNV_PARENT=<chrom:pos:ref:alt> so variant_filter.py can
                 set Filter MNV_COMPONENT and let the MNV inherit BLACKLIST /
                 COMMON_POLYMORPHISM from its parts

A run with no evidence is left untouched. Runs longer than two SNVs are
tested whole first, then as adjacent pairs.

Stdlib only; Python 3.6 (GATK container). Reference bases are read through
the .fai index without pysam.
"""

import argparse
import gzip
import sys
from collections import OrderedDict

MAX_GAP = 2
CALLER_ORDER = ["M", "V", "D", "K", "F", "P", "I", "S"]   # MVDKFP + Pindel, DeepSomatic (8 flags)
FILTER_RANK = {"PASS": 0, "LowQual": 1, "REJECT": 2}


def opener(path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)


class Fasta(object):
    """Minimal .fai-indexed FASTA reader (1-based, inclusive)."""

    def __init__(self, path):
        self.path = path
        self.index = {}
        with open(path + ".fai") as fh:
            for line in fh:
                name, length, offset, linebases, linewidth = line.split("\t")[:5]
                self.index[name] = (int(length), int(offset), int(linebases), int(linewidth))
        self.fh = open(path, "rb")

    def fetch(self, chrom, start, end):
        length, offset, linebases, linewidth = self.index[chrom]
        if start < 1 or end > length or end < start:
            raise ValueError("bad interval %s:%d-%d" % (chrom, start, end))
        out = []
        pos = start - 1
        while pos < end:
            line_no, in_line = divmod(pos, linebases)
            self.fh.seek(offset + line_no * linewidth + in_line)
            take = min(linebases - in_line, end - pos)
            out.append(self.fh.read(take).decode())
            pos += take
        return "".join(out).upper()


def parse_info(s):
    d = OrderedDict()
    for item in s.split(";"):
        if not item or item == ".":
            continue
        if "=" in item:
            k, v = item.split("=", 1)
            d[k] = v
        else:
            d[item] = None
    return d


def format_info(d):
    parts = []
    for k, v in d.items():
        parts.append(k if v is None else "%s=%s" % (k, v))
    return ";".join(parts) if parts else "."


def read_mnv_and_phase(path, want_phase):
    """From a caller VCF return ({(chrom,pos,ref,alt)}, {(chrom,pos,ref,alt): (PID,PGT)})."""
    mnvs = set()
    phase = {}
    if not path:
        return mnvs, phase
    with opener(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            chrom, pos, ref, alts = c[0], int(c[1]), c[3], c[4]
            for alt in alts.split(","):
                if len(ref) > 1 and len(ref) == len(alt):
                    mnvs.add((chrom, pos, ref, alt))
                elif want_phase and len(ref) == 1 and len(alt) == 1 and len(c) >= 10:
                    keys = c[8].split(":")
                    vals = c[9].split(":")
                    fmt = dict(zip(keys, vals))
                    if fmt.get("PID") and fmt.get("PGT"):
                        phase[(chrom, pos, ref, alt)] = (fmt["PID"], fmt["PGT"])
    return mnvs, phase


def worst_filter(filters):
    return max(filters, key=lambda f: FILTER_RANK.get(f, 1))


def build_mnv(run, fasta, m2_mnvs, vd_mnvs, m2_phase):
    """run: list of consensus record dicts (sorted by pos). Returns (record, evidence) or None."""
    chrom = run[0]["chrom"]
    start, end = run[0]["pos"], run[-1]["pos"]
    ref = fasta.fetch(chrom, start, end)
    alt = list(ref)
    for r in run:
        i = r["pos"] - start
        if ref[i] != r["ref"]:
            return None   # consensus ref disagrees with the reference; do not merge
        alt[i] = r["alt"]
    alt = "".join(alt)
    key = (chrom, start, ref, alt)

    ev = []
    if key in m2_mnvs:
        ev.append("MUTECT2_MNV")
    if key in vd_mnvs:
        ev.append("VARDICT_MNV")
    pids = [m2_phase.get((r["chrom"], r["pos"], r["ref"], r["alt"])) for r in run]
    if all(pids) and len(set(pids)) == 1:
        ev.append("MUTECT2_PID")
    if not ev:
        return None

    flags = ["1"] * 8
    for r in run:
        f = r["info"].get("MVDKFP", ",".join(["0"] * 8)).split(",")
        flags = ["1" if (a == "1" and b == "1") else "0" for a, b in zip(flags, f)]
    if "MUTECT2_MNV" in ev or "MUTECT2_PID" in ev:
        flags[0] = "1"
    if "VARDICT_MNV" in ev:
        flags[2] = "1"
    num_tools = sum(1 for x in flags if x == "1")

    lowest = min(run, key=lambda r: r["af"])
    info = OrderedDict()
    if any("SOMATIC" in r["info"] for r in run):
        info["SOMATIC"] = None
    info["MVDKFP"] = ",".join(flags)
    info["NUM_TOOLS"] = str(num_tools)
    lcs = [r["info"].get("LC") for r in run if r["info"].get("LC")]
    if lcs:
        info["LC"] = min(lcs, key=float)
    info["AF"] = "%.4g" % lowest["af"]
    info["MNV_OF"] = ",".join(str(r["pos"]) for r in run)
    info["MNV_EVIDENCE"] = "|".join(ev)

    rec = {
        "chrom": chrom, "pos": start, "id": ".", "ref": ref, "alt": alt,
        "qual": lowest["cols"][5], "filter": worst_filter([r["cols"][6] for r in run]),
        "info": info, "cols": lowest["cols"],
    }
    return rec, "|".join(ev)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--consensus", required=True)
    ap.add_argument("--mutect2-raw", default=None)
    ap.add_argument("--vardict", default=None)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-gap", type=int, default=MAX_GAP)
    args = ap.parse_args(argv)

    fasta = Fasta(args.reference)
    m2_mnvs, m2_phase = read_mnv_and_phase(args.mutect2_raw, want_phase=True)
    vd_mnvs, _ = read_mnv_and_phase(args.vardict, want_phase=False)

    header = []
    records = []
    with open(args.consensus) as fh:
        for line in fh:
            if line.startswith("#"):
                header.append(line)
                continue
            cols = line.rstrip("\n").split("\t")
            info = parse_info(cols[7])
            try:
                af = float(info.get("AF", "nan"))
            except ValueError:
                af = float("nan")
            records.append({
                "chrom": cols[0], "pos": int(cols[1]), "id": cols[2], "ref": cols[3], "alt": cols[4],
                "qual": cols[5], "filter": cols[6], "info": info, "cols": cols, "af": af,
                "is_snv": len(cols[3]) == 1 and len(cols[4]) == 1 and cols[3] != "-" and cols[4] != "-",
            })

    # candidate runs: consecutive SNVs, same chromosome, position difference <= max_gap
    snvs = sorted([r for r in records if r["is_snv"]], key=lambda r: (r["chrom"], r["pos"]))
    runs = []
    cur = []
    for r in snvs:
        if cur and r["chrom"] == cur[-1]["chrom"] and 0 < r["pos"] - cur[-1]["pos"] <= args.max_gap:
            cur.append(r)
        else:
            if len(cur) >= 2:
                runs.append(cur)
            cur = [r]
    if len(cur) >= 2:
        runs.append(cur)

    merged = []      # (first component record, new record)
    n_runs = len(runs)
    ev_counts = {}
    for run in runs:
        candidates = [run] if len(run) == 2 else [run] + [run[i:i + 2] for i in range(len(run) - 1)]
        done = False
        for cand in candidates:
            if done and cand is not run:
                break
            res = build_mnv(cand, fasta, m2_mnvs, vd_mnvs, m2_phase)
            if res is None:
                continue
            rec, ev = res
            parent = "%s:%d:%s:%s" % (rec["chrom"], rec["pos"], rec["ref"], rec["alt"])
            for r in cand:
                r["info"]["MNV_PARENT"] = parent
            merged.append((cand[0], rec))
            ev_counts[ev] = ev_counts.get(ev, 0) + 1
            if cand is run:
                done = True

    # write: header + new INFO lines, records in original order, MNV inserted before its first component
    new_before = {}
    for first, rec in merged:
        new_before.setdefault(id(first), []).append(rec)

    def emit(rec):
        cols = list(rec["cols"])
        cols[0], cols[1], cols[2], cols[3], cols[4] = rec["chrom"], str(rec["pos"]), rec["id"], rec["ref"], rec["alt"]
        cols[5], cols[6], cols[7] = rec["qual"], rec["filter"], format_info(rec["info"])
        return "\t".join(cols) + "\n"

    info_lines = [
        '##INFO=<ID=MNV_OF,Number=.,Type=Integer,Description="MNV_MERGE_V1: positions of the consensus SNVs merged into this record">\n',
        '##INFO=<ID=MNV_EVIDENCE,Number=1,Type=String,Description="MNV_MERGE_V1: MUTECT2_MNV, VARDICT_MNV and/or MUTECT2_PID (shared phase set)">\n',
        '##INFO=<ID=MNV_PARENT,Number=1,Type=String,Description="MNV_MERGE_V1: this SNV is a component of the MNV record chrom:pos:ref:alt">\n',
    ]
    with open(args.out, "w") as out:
        for line in header:
            if line.startswith("#CHROM"):
                out.writelines(info_lines)
            out.write(line)
        for r in records:
            for rec in new_before.get(id(r), []):
                out.write(emit(rec))
            out.write(emit(r))

    sys.stderr.write("[mnv_merge] %s: %d consensus records, %d SNV runs within %d bp, %d MNV records added (%s); "
                     "Mutect2 raw: %d MNVs, %d phased SNVs; VarDict: %d MNVs\n"
                     % (args.sample, len(records), n_runs, args.max_gap, len(merged),
                        ", ".join("%s %d" % kv for kv in sorted(ev_counts.items())) or "none",
                        len(m2_mnvs), len(m2_phase), len(vd_mnvs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
