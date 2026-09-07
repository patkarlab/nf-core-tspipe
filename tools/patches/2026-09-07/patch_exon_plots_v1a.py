#!/usr/bin/env python3
"""patch_exon_plots_v1a.py -- renderer version line in the EXON_PLOTS script (MARKER EXON_PLOTS_V1a)
so the task re-executes after bin/plot_exon_ratio.py changed (rows at gene boundaries, v1.3)."""
import argparse, datetime, re, shutil, sys
MARKER = "MARKER EXON_PLOTS_V1a"; TARGET = "modules/local/exon_plots.nf"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default=TARGET); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); t = open(a.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    rx = re.compile(r"^(?P<i>[ \t]*)plot_exon_ratio_batch\.py \\\\$", re.M)
    if len(rx.findall(t)) != 1:
        print("[error] anchor: %d matches" % len(rx.findall(t))); sys.exit(1)
    t2 = rx.sub(lambda m: "%s# exon renderer version: EXONPLOT_V1.3 rows at gene boundaries (bash comment; busts the task cache)\n%splot_exon_ratio_batch.py \\\\" % (m.group("i"), m.group("i")), t, count=1)
    t2 = t2.replace(" * modules/local/exon_plots.nf  (EXON_PLOTS_V1)", " * modules/local/exon_plots.nf  (EXON_PLOTS_V1; %s)" % MARKER, 1)
    blocks = t2.split('"""'); bad = [l for b in blocks[1::2] for l in b.splitlines() if re.search(r'\S\s+//', l)]
    print("[ok] version line added; markers %d; '//' in script: %d" % (t2.count(MARKER), len(bad)))
    if t2.count(MARKER) != 1 or bad:
        print("[error] verification failed"); sys.exit(1)
    if not a.apply:
        print("[dry-run]"); sys.exit(0)
    b = "%s.bak_exon_plots_v1a_%s" % (a.target, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(a.target, b); open(a.target, "w").write(t2); print("[patch] wrote %s" % a.target)

if __name__ == "__main__":
    main()
