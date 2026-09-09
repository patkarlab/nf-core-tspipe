#!/usr/bin/env python3
"""HARDEN_Q5_V1 offline check for bin/annotate.py (audit Q5).

Replays a cached VEP_ANNOTATE task from its work directory with run_vep() and
run_annovar() stubbed -- their outputs (<sample>.vep.vcf, <sample>.hg38_multianno.txt)
are already in the work dir, so nothing slow is executed:

  A  run_annovar returns 1                    -> main() must exit 1
  B  ANNOVAR exits 0 but multianno is absent  -> main() must exit 1
  C  both succeed                             -> output TSV byte-identical to the cached annotated.tsv
  D  real run_annovar() with an empty --annovar-db -> returns 1 before invoking perl;
     with allow_missing_db=True it falls through to "No ANNOVAR databases" and returns 1

Nothing in the work directory is modified: every input is symlinked into a
temporary directory and annotate.py runs there.

Usage (gandalf, repo root):
    /home/hemat/anaconda3/envs/targeted-seq/bin/python tools/patches/2026-09-09/check_annovar_fatal.py \\
        --workdir /goast/hemat_data/nf-core-tspipe/work/xx/yyyy...   [--repo .]
"""
import argparse
import hashlib
import importlib.util
import os
import re
import shlex
import shutil
import sys
import tempfile


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def annotate_argv(workdir):
    """Recover annotate.py's argument list from the task's .command.sh."""
    with open(os.path.join(workdir, ".command.sh")) as f:
        text = f.read()
    text = re.sub(r"\\\n\s*", " ", text)          # join line continuations
    for line in text.splitlines():
        if "annotate.py" in line and not line.strip().startswith("#"):
            toks = shlex.split(line)
            for i, t in enumerate(toks):
                if t.endswith("annotate.py"):
                    return toks[i + 1:]
    raise SystemExit("[error] no annotate.py invocation found in %s/.command.sh" % workdir)


def arg_value(argv, *names):
    for n in names:
        if n in argv:
            return argv[argv.index(n) + 1]
    return None


def explain_difference(cached, new, script):
    """Diagnostics for a C mismatch: a cached task older than annotate.py's last
    change differs by construction (the task was produced by older code); a
    same-vintage mismatch is a real regression."""
    import time
    fmt = lambda t: time.strftime("%Y-%m-%d %H:%M", time.localtime(t))
    print("    cached output written %s; bin/annotate.py last changed %s" % (
        fmt(os.path.getmtime(cached)), fmt(os.path.getmtime(script))))
    if os.path.getmtime(cached) < os.path.getmtime(script):
        print("    NOTE: the cached task predates the current annotate.py -- pick the task from the "
              "latest resume (sort `nextflow log` by submit time) before reading anything into this")
    with open(cached) as a, open(new) as b:
        la, lb = a.read().split("\n"), b.read().split("\n")
    print("    rows: cached %d, new %d" % (len(la) - 1, len(lb) - 1))
    if la[0] != lb[0]:
        ca, cb = la[0].split("\t"), lb[0].split("\t")
        print("    header differs: cached %d columns, new %d; only in cached: %s; only in new: %s" % (
            len(ca), len(cb), ",".join(sorted(set(ca) - set(cb))) or "-", ",".join(sorted(set(cb) - set(ca))) or "-"))
        return
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            cols = la[0].split("\t")
            xa, ya = x.split("\t"), y.split("\t")
            diffcols = [cols[j] for j in range(min(len(xa), len(ya))) if xa[j] != ya[j]]
            print("    first differing line %d; columns: %s" % (i + 1, ", ".join(diffcols[:12]) or "(row length)"))
            for c in diffcols[:4]:
                j = cols.index(c)
                print("      %s: cached %r  new %r" % (c, xa[j][:60], ya[j][:60]))
            return


def load_module(path):
    spec = importlib.util.spec_from_file_location("annotate_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_main(mod, argv):
    """Run mod.main() with argv; return the exit code (0 when main returns normally)."""
    saved = sys.argv
    sys.argv = ["annotate.py"] + argv
    try:
        mod.main()
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", required=True, help="work directory of a cached VEP_ANNOTATE task")
    ap.add_argument("--repo", default=".", help="nf-core-tspipe repo root (bin/annotate.py is taken from here)")
    args = ap.parse_args()

    workdir = os.path.abspath(args.workdir)
    script = os.path.join(os.path.abspath(args.repo), "bin", "annotate.py")
    for p in (workdir, script, os.path.join(workdir, ".command.sh")):
        if not os.path.exists(p):
            raise SystemExit("[error] not found: %s" % p)
    src = open(script).read()
    if "HARDEN_Q5_V1" not in src:
        raise SystemExit("[error] %s does not carry HARDEN_Q5_V1 -- apply the patcher first" % script)

    argv = annotate_argv(workdir)
    sample = arg_value(argv, "-s", "--sample-name")
    out_name = arg_value(argv, "-o", "--output") or (sample + ".annotated.tsv")
    cached_out = os.path.join(workdir, out_name)
    multianno = sample + ".hg38_multianno.txt"
    for name in (sample + ".vep.vcf", multianno, out_name):
        if not os.path.isfile(os.path.join(workdir, name)):
            raise SystemExit("[error] expected cached file missing in work dir: %s" % name)
    print("[info] sample %s, cached output %s (%s)" % (sample, out_name, md5(cached_out)))

    tmp = tempfile.mkdtemp(prefix="q5_check_")
    for name in os.listdir(workdir):
        if name.startswith("."):
            continue
        os.symlink(os.path.join(workdir, name), os.path.join(tmp, name))
    # the run under test writes its own output; do not let it hit the cached file's symlink
    os.unlink(os.path.join(tmp, out_name))
    os.chdir(tmp)

    mod = load_module(script)
    mod.run_vep = lambda *a, **k: 0        # <sample>.vep.vcf is already present
    real_run_annovar = mod.run_annovar
    failures = []

    # A: ANNOVAR non-zero exit must be fatal
    mod.run_annovar = lambda *a, **k: 1
    rc = run_main(mod, argv)
    print("[A] run_annovar -> 1: exit %d (expected 1)" % rc)
    if rc != 1:
        failures.append("A")

    # B: ANNOVAR exit 0 with no multianno file must be fatal
    mod.run_annovar = lambda *a, **k: 0
    os.unlink(os.path.join(tmp, multianno))
    rc = run_main(mod, argv)
    print("[B] multianno absent: exit %d (expected 1)" % rc)
    if rc != 1:
        failures.append("B")
    os.symlink(os.path.join(workdir, multianno), os.path.join(tmp, multianno))

    # C: success path reproduces the cached output byte for byte
    rc = run_main(mod, argv)
    new_out = os.path.join(tmp, out_name)
    same = rc == 0 and os.path.isfile(new_out) and md5(new_out) == md5(cached_out)
    print("[C] success path: exit %d, output %s cached (%s)" % (
        rc, "identical to" if same else "DIFFERS from", md5(new_out) if os.path.isfile(new_out) else "no output"))
    if not same:
        failures.append("C")
        if os.path.isfile(new_out):
            explain_difference(cached_out, new_out, script)

    # D: real run_annovar with an empty database directory
    empty_db = tempfile.mkdtemp(prefix="q5_empty_db_")
    vcf = arg_value(argv, "--somaticseq-vcf")
    script_arg = arg_value(argv, "--annovar-script")
    rc_strict = real_run_annovar(vcf, "q5_test", script_arg, empty_db)
    rc_lenient = real_run_annovar(vcf, "q5_test", script_arg, empty_db, allow_missing_db=True)
    print("[D] empty --annovar-db: strict rc %d (expected 1), --annovar-allow-missing-db rc %d (expected 1, 'No ANNOVAR databases')"
          % (rc_strict, rc_lenient))
    if rc_strict != 1 or rc_lenient != 1:
        failures.append("D")
    shutil.rmtree(empty_db, ignore_errors=True)

    os.chdir("/")
    shutil.rmtree(tmp, ignore_errors=True)
    if failures:
        print("[FAIL] %s" % ", ".join(failures))
        sys.exit(1)
    print("[PASS] HARDEN_Q5_V1: A B C D")


if __name__ == "__main__":
    main()
