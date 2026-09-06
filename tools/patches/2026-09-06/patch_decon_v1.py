#!/usr/bin/env python3
"""
patch_decon_v1.py -- wire the DECoN exon-level arm E (MARKER DECON_V1).
Gap register A5 / handoff item 6 prerequisite.

Files (3), all-or-nothing:
  conf/twist_apply.config     params decon_pool_male/female, decon_exons_bed,
                              decon_trans_prob, decon_min_corr, decon_min_cov,
                              decon_bf; process DECON: host 'decon' env
                              (container = null, PATH override), publishDir
  workflows/tspipe.nf         DECON block inside the twist gate (on
                              params.decon_pool_male), female pool through
                              sexstratFemale(); ch_decon_genes joined into
                              the consensus input (empty placeholder when
                              DECoN is not configured)
  modules/local/cnv_consensus_multi.nf
                              tuple gains path(decon_genes); --decon-genes
                              passed only when a file is present

Requires SEXSTRAT_V1 and PCN_SEX_V1 (sexstratFemale, cnv_sex_fallback) and
CMX_V2 (--decon-genes). Dry run by default; --apply writes with
.bak_decon_v1_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER DECON_V1"
TAG = "DECON_V1"


def sub_once(text, pattern, repl, label, flags=re.M, required=True):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n == 0 and not required:
        return text, "[warn] optional anchor not found, skipped: %s" % label
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


PARAMS_BLOCK = '''
{i}// {m}: exon-level arm E (DECoN/ExomeDepth); defining decon_pool_male is
{i}// the gate. Pools from tools/decon/build_decon_pool.sh --sex male|female.
{i}decon_pool_male    = "${{projectDir}}/assets/twist_myeloid/decon_pool_male.RData"
{i}decon_pool_female  = "${{projectDir}}/assets/twist_myeloid/decon_pool_female.RData"
{i}decon_exons_bed    = "${{projectDir}}/assets/twist_myeloid/decon_exons.bed"
{i}decon_trans_prob   = 0.01
{i}decon_min_corr     = 0.98
{i}decon_min_cov      = 100
{i}decon_bf           = 12'''

PROCESS_BLOCK = '''{i}// {m}: DECoN on the host 'decon' env (r-base 4.3, ExomeDepth 1.1.16);
{i}// targeted-seq kept on PATH for python3. Literal paths per the -c
{i}// eager-params gotcha.
{i}withName: 'DECON' {{
{i}    container    = null
{i}    beforeScript = 'export PATH=/home/hemat/anaconda3/envs/decon/bin:/home/hemat/anaconda3/envs/targeted-seq/bin:$PATH'
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_decon" }},
{i}        mode: 'link',
{i}        pattern: '*.decon*'
{i}    ]
{i}}}
'''

TSPIPE_BLOCK = '''{i}// {m}: exon-level arm E (DECoN); gated on params.decon_pool_male.
{i}// Without it, or while the pool asset is not built yet, the consensus
{i}// receives an empty placeholder and omits E (one log.warn).
{i}def decon_enabled = params.containsKey('decon_pool_male') && params.decon_pool_male && file(params.decon_pool_male).exists()
{i}if( params.containsKey('decon_pool_male') && params.decon_pool_male && !decon_enabled )
{i}    log.warn "[DECON] pool not found: ${{params.decon_pool_male}}; arm E disabled for this run"
{i}if( decon_enabled ) {{
{i}    ch_decon_exons     = Channel.value(file(params.decon_exons_bed, checkIfExists: true))
{i}    ch_decon_pool_male = Channel.value(file(params.decon_pool_male, checkIfExists: true))
{i}    def decon_pool_female = (params.containsKey('decon_pool_female') && params.decon_pool_female) ? params.decon_pool_female : null
{i}    ch_decon_pool_female = Channel.value( sexstratFemale(decon_pool_female,
{i}        "${{projectDir}}/assets/${{params.panel}}/decon_pool_female.RData", params.decon_pool_male) )
{i}    ch_paralog_exons = Channel.value(file("${{projectDir}}/assets/${{params.panel}}/paralog_limited_exons.tsv", checkIfExists: true))
{i}    DECON( ch_final_bam, ch_reference, ch_decon_exons, ch_decon_pool_male, ch_decon_pool_female, ch_paralog_exons )
{i}    ch_decon_genes = DECON.out.genes
{i}}} else {{
{i}    ch_decon_genes = ch_final_bam.map {{ m, _b, _i -> [ m, [] ] }}
{i}}}

'''


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(
        t,
        r'^(?P<i>[ \t]*)purecn_normaldb_female[ \t]*=[ \t]*".*"[ \t]*// MARKER PCN_SEX_V1[ \t]*$',
        lambda m: m.group(0) + PARAMS_BLOCK.format(i=m.group("i"), m=MARKER),
        "twist_apply.config: DECoN params after purecn_normaldb_female")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)withName: 'CNV_CONSENSUS_MULTI' \{[ \t]*$",
        lambda m: PROCESS_BLOCK.format(i=m.group("i"), m=TAG) + m.group(0),
        "twist_apply.config: DECON process block before CNV_CONSENSUS_MULTI")
    notes.append(n)
    return t, notes, 1


def patch_tspipe(t):
    notes = []
    if "sexstratFemale" not in t:
        raise ValueError("tspipe.nf lacks sexstratFemale (apply SEXSTRAT_V1 first)")
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)// CMX_V1: five-caller consensus \+ Phase-4 JSON payload\.[ \t]*$",
        lambda m: TSPIPE_BLOCK.format(i=m.group("i"), m=MARKER) + m.group(0),
        "tspipe.nf: DECON block before the consensus")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)\.join\( PURECN\.out\.summary,[ \t]*by: 0 \)[ \t]*$",
        lambda m: m.group(0) + "\n%s.join( ch_decon_genes,                        by: 0 )   // %s" % (m.group("i"), TAG),
        "tspipe.nf: consensus join gains ch_decon_genes")
    notes.append(n)
    return t, notes, 1


def patch_consensus_nf(t):
    notes = []
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)path\(purecn_genes\), path\(purecn_summary\)[ \t]*$",
        lambda m: "%spath(purecn_genes), path(purecn_summary),\n%spath(decon_genes)   // %s (empty list when DECoN is off)" % (m.group("i"), m.group("i"), MARKER),
        "cnv_consensus_multi.nf: tuple gains decon_genes")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)def loo_use = \(stratum == 'female'\) \? loo_summary_female : loo_summary[ \t]*$",
        lambda m: m.group(0) + "\n%sdef decon_arg = decon_genes ? \"--decon-genes ${decon_genes}\" : ''   // %s" % (m.group("i"), TAG),
        "cnv_consensus_multi.nf: decon_arg")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)--purecn-summary \$\{purecn_summary\} \\\\[ \t]*$",
        lambda m: m.group(0) + "\n%s${decon_arg} \\\\" % m.group("i"),
        "cnv_consensus_multi.nf: --decon-genes")
    notes.append(n)
    t, n = sub_once(t, r"^ \* modules/local/cnv_consensus_multi\.nf  \(CMX_V1; PureCN inputs PCN_V1\)$",
                    " * modules/local/cnv_consensus_multi.nf  (CMX_V2 arms K/G/B/P/E; PureCN PCN_V1; DECoN DECON_V1)",
                    "cnv_consensus_multi.nf: header", required=False)
    notes.append(n)
    return t, notes, 1


FILES = [
    ("conf/twist_apply.config",              patch_twist_apply),
    ("workflows/tspipe.nf",                  patch_tspipe),
    ("modules/local/cnv_consensus_multi.nf", patch_consensus_nf),
]


def brace_balance(text):
    return text.count("{") - text.count("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    planned, failed = [], False
    for rel, fn in FILES:
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found"); failed = True; continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER); continue
        try:
            new_text, notes, expected = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        b0, b1 = brace_balance(original), brace_balance(new_text)
        print("   [check] markers %d (expected %d); brace balance %d/%d" % (new_text.count(MARKER), expected, b0, b1))
        if new_text.count(MARKER) != expected or b0 != b1:
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned))
        for path, original, new_text in planned:
            old_set = set(original.splitlines())
            print("## %s" % os.path.relpath(path, args.root))
            for line in new_text.splitlines():
                if line not in old_set:
                    print("+ " + line)
        sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_decon_v1_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
