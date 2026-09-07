#!/usr/bin/env python3
"""
patch_hmf_purple_v1.py -- PURPLE as consensus arm H (MARKER HMF_PURPLE_V1).
Handoff item 11.

Files (4), all-or-nothing:
  bin/cnv_consensus_multi.py           --purple-genes/--purple-summary; arm H
                                       (trusted when status has no FAIL_);
                                       h_loh with cn near expected -> cnLOH
                                       support; columns h_call h_cn_min
                                       h_cn_max h_macn_min h_loh
  modules/local/cnv_consensus_multi.nf tuple gains path(purple_genes),
                                       path(purple_summary); args passed when present
  workflows/tspipe.nf                  HMF block gated on the panel normalisation
                                       asset existing: HMF_AMBER, HMF_COBALT,
                                       HMF_PURPLE; ch_purple_genes/summary joined
                                       into the consensus input (empty placeholders
                                       when off)
  conf/twist_apply.config              params hmf_* ; process HMF_.* host env; publishDir cnv_hmftools/

Requires CMX_V2_1, CNV_BLACKLIST_V1 (consensus), DECON_V1 (join shape).
Dry run by default; --apply writes .bak_hmf_purple_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER HMF_PURPLE_V1"
TAG = "HMF_PURPLE_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


# ---------------------------------------------------------------- consensus script
PURPLE_LOAD = '''    # ---- %s: PURPLE (hmftools) arm H; optional; FAIL_ status -> advisory
    purple_h = {}
    purple_h_sum = {"status": "ABSENT"}
    h_trusted = False
    if args.purple_summary and os.path.isfile(args.purple_summary):
        hs_rows = read_tsv(args.purple_summary)[1]
        if hs_rows:
            purple_h_sum = hs_rows[0]
    if args.purple_genes and os.path.isfile(args.purple_genes):
        for r in read_tsv(args.purple_genes)[1]:
            purple_h[r["gene"]] = r
        h_trusted = str(purple_h_sum.get("trusted", "")).strip().upper() == "TRUE"
        if not h_trusted:
            warn("PURPLE status={0}; H calls retained as advisory, H support omitted".format(purple_h_sum.get("status")))
        else:
            print("[ok] PURPLE arm H: status={0} purity={1} ploidy={2}".format(
                purple_h_sum.get("status"), purple_h_sum.get("purity"), purple_h_sum.get("ploidy")))

''' % MARKER


def patch_consensus_py(t):
    notes = []
    t, n = sub_once(t, r'^    ap\.add_argument\("--gene-blacklist", default=None,\n[^\n]*\n',
                    lambda m: m.group(0)
                    + '    ap.add_argument("--purple-genes", default=None, help="PURPLE arm H gene table (%s); optional")\n' % TAG
                    + '    ap.add_argument("--purple-summary", default=None, help="PURPLE arm H summary (%s); optional")\n' % TAG,
                    "argparse --purple-genes/--purple-summary")
    notes.append(n)
    t, n = sub_once(t, r'^    # ---- per-gene consensus \(CMX_V2: depth K/G; independent B/P/E; tier rule\)\n',
                    lambda m: PURPLE_LOAD + m.group(0), "load PURPLE tables")
    notes.append(n)
    t, n = sub_once(t, r'^        e_bf = dr\.get\("e_bf", "NA"\) if dr else "NA"\n',
                    lambda m: m.group(0)
                    + '        hr = purple_h.get(g["gene"], {})\n'
                    + '        h_call = hr.get("h_call", "NA")\n'
                    + '        h_loh = str(hr.get("h_loh", "")).strip().upper() == "TRUE"\n'
                    + '        h_cnloh = h_trusted and h_loh and h_call == "NEUTRAL"\n',
                    "per-gene H values")
    notes.append(n)
    t, n = sub_once(t, r'^                 "E": e_call if e_call in \("GAIN", "LOSS"\) else None\}\n',
                    '                 "E": e_call if e_call in ("GAIN", "LOSS") else None,\n'
                    '                 "H": h_call if (h_trusted and h_call in ("GAIN", "LOSS")) else None}\n',
                    "indep arms gain H")
    notes.append(n)
    t, n = sub_once(t, r'^        cnloh_arms = \[a for a, v in \(\("B", b_call == "CNLOH"\), \("P", p_cnloh\)\) if v\]\n',
                    '        cnloh_arms = [a for a, v in (("B", b_call == "CNLOH"), ("P", p_cnloh), ("H", h_cnloh)) if v]\n',
                    "cnLOH arms gain H")
    notes.append(n)
    t, n = sub_once(t, r'^            "e_call": e_call, "e_bf": e_bf,\n',
                    lambda m: m.group(0)
                    + '            "h_call": h_call, "h_cn_min": hr.get("h_cn_min", "NA"),\n'
                    + '            "h_cn_max": hr.get("h_cn_max", "NA"), "h_macn_min": hr.get("h_macn_min", "NA"),\n'
                    + '            "h_loh": "TRUE" if h_loh else ("FALSE" if hr else "NA"),\n',
                    "gene dict H columns")
    notes.append(n)
    t, n = sub_once(t, r'^        "p_call", "p_C", "p_loh", "e_call", "e_bf", "support",\n',
                    '        "p_call", "p_C", "p_loh", "e_call", "e_bf",\n'
                    '        "h_call", "h_cn_min", "h_cn_max", "h_macn_min", "h_loh", "support",\n',
                    "genes.tsv columns")
    notes.append(n)
    t, n = sub_once(t, r'^        "purecn": purecn_sum,\n',
                    lambda m: m.group(0) + '        "purple": purple_h_sum,\n', "JSON purple summary")
    notes.append(n)
    t, n = sub_once(t, r'^        "schema": "twist_cnv_consensus4/v3",$', '        "schema": "twist_cnv_consensus4/v4",', "schema v4 (payload line)")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- consensus module
def patch_consensus_nf(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)path\(decon_genes\)   // MARKER DECON_V1 \(empty list when DECoN is off\)[ \t]*$",
                    lambda m: "%spath(decon_genes),   // MARKER DECON_V1 (empty list when DECoN is off)\n%spath(purple_genes), path(purple_summary)   // %s (empty lists when hmftools is off)"
                    % (m.group("i"), m.group("i"), MARKER),
                    "tuple gains purple inputs")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)def blacklist_arg = gene_blacklist \? \"--gene-blacklist \$\{gene_blacklist\}\" : ''[^\n]*$",
                    lambda m: m.group(0) + "\n%sdef purple_arg = (purple_genes && purple_summary) ? \"--purple-genes ${purple_genes} --purple-summary ${purple_summary}\" : ''   // %s" % (m.group("i"), TAG),
                    "purple_arg")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)\$\{blacklist_arg\} \\\\[ \t]*$',
                    lambda m: m.group(0) + "\n%s${purple_arg} \\\\" % m.group("i"), "script arg")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- tspipe
TSPIPE_BLOCK = '''{i}// {m}: hmftools AMBER -> COBALT -> PURPLE (tumour-only, targeted) as
{i}// consensus arm H. Gated on the panel's COBALT normalisation asset existing.
{i}def hmf_norm_path = params.containsKey('hmf_target_norm') ? params.hmf_target_norm : "${{projectDir}}/assets/${{params.panel}}/hmftools/target_regions.cobalt_normalisation.twist_myeloid.38.tsv"
{i}def hmf_enabled = params.containsKey('hmf_resources') && params.hmf_resources && file(hmf_norm_path).exists()
{i}if( params.containsKey('hmf_resources') && params.hmf_resources && !hmf_enabled )
{i}    log.warn "[HMF] normalisation asset not found: ${{hmf_norm_path}}; arm H disabled for this run"
{i}if( hmf_enabled ) {{
{i}    ch_hmf_loci      = Channel.value(file(params.hmf_loci,        checkIfExists: true))
{i}    ch_hmf_gc        = Channel.value(file(params.hmf_gc_profile,  checkIfExists: true))
{i}    ch_hmf_ensembl   = Channel.value(file(params.hmf_ensembl_dir, checkIfExists: true))
{i}    ch_hmf_hotspots  = Channel.value(file(params.hmf_hotspots,    checkIfExists: true))
{i}    ch_hmf_target    = Channel.value(file(params.hmf_target_bed,  checkIfExists: true))
{i}    ch_hmf_norm      = Channel.value(file(hmf_norm_path,          checkIfExists: true))
{i}    ch_hmf_drivers   = Channel.value(file(params.hmf_driver_panel, checkIfExists: true))
{i}    HMF_AMBER( ch_final_bam, ch_reference, ch_hmf_loci, ch_hmf_target )
{i}    HMF_COBALT( ch_final_bam, ch_reference, ch_hmf_gc, ch_hmf_norm )
{i}    HMF_PURPLE( HMF_AMBER.out.dir.join( HMF_COBALT.out.dir, by: 0 ), ch_reference, ch_hmf_gc, ch_hmf_ensembl,
{i}                ch_hmf_drivers, ch_hmf_hotspots, ch_hmf_target, ch_hmf_norm )
{i}    ch_purple_genes   = HMF_PURPLE.out.genes
{i}    ch_purple_summary = HMF_PURPLE.out.summary
{i}}} else {{
{i}    ch_purple_genes   = ch_final_bam.map {{ m, _b, _i -> [ m, [] ] }}
{i}    ch_purple_summary = ch_final_bam.map {{ m, _b, _i -> [ m, [] ] }}
{i}}}

'''


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r"^include \{ EXON_PLOTS\s*\} from '\.\./modules/local/exon_plots'[^\n]*$",
                    lambda m: m.group(0)
                    + "\ninclude { HMF_AMBER           } from '../modules/local/hmf_amber'             // %s\n" % MARKER
                    + "include { HMF_COBALT          } from '../modules/local/hmf_cobalt'\n"
                    + "include { HMF_PURPLE          } from '../modules/local/hmf_purple'",
                    "includes")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)// CMX_V1: five-caller consensus \+ Phase-4 JSON payload\.[ \t]*$",
                    lambda m: TSPIPE_BLOCK.format(i=m.group("i"), m=TAG) + m.group(0), "HMF block before the consensus")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\.join\( ch_decon_genes,[ \t]*by: 0 \)   // DECON_V1[ \t]*$",
                    lambda m: m.group(0) + "\n%s.join( ch_purple_genes,                       by: 0 )   // %s\n%s.join( ch_purple_summary,                     by: 0 )" % (m.group("i"), TAG, m.group("i")),
                    "consensus join gains purple")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- twist_apply
PARAMS = '''
{i}// {m}: hmftools stack (AMBER 4.3 / COBALT 3.0 / PURPLE 4.4 in the host env
{i}// 'hmftools'); defining hmf_resources is the gate, the normalisation asset must exist.
{i}hmf_env           = '/home/hemat/anaconda3/envs/hmftools'
{i}hmf_resources     = '/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8'
{i}hmf_loci          = '/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8/dna/copy_number/AmberGermlineSites.38.tsv.gz'
{i}hmf_gc_profile    = '/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8/dna/copy_number/GC_profile.1000bp.38.cnp'
{i}hmf_ensembl_dir   = '/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8/common/ensembl_data'
{i}hmf_hotspots      = '/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8/dna/variants/KnownHotspots.somatic.38.vcf.gz'
{i}hmf_target_bed    = "${{projectDir}}/assets/twist_myeloid/hmftools/target_regions.twist_myeloid.38.bed"
{i}hmf_target_norm   = "${{projectDir}}/assets/twist_myeloid/hmftools/target_regions.cobalt_normalisation.twist_myeloid.38.tsv"
{i}hmf_driver_panel  = "${{projectDir}}/assets/twist_myeloid/hmftools/DriverGenePanel.twist_myeloid.38.tsv"
{i}hmf_pcf_gamma     = 50'''

PROCESS = '''{i}// {m}: hmftools on the host 'hmftools' env (Java 21); targeted-seq kept for python3
{i}withName: 'HMF_.*' {{
{i}    container    = null
{i}    beforeScript = 'export PATH=/home/hemat/anaconda3/envs/hmftools/bin:/home/hemat/anaconda3/envs/targeted-seq/bin:$PATH'
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_hmftools" }},
{i}        mode: 'copy',
{i}        pattern: '{{amber,cobalt,purple,*.purple.h_*.tsv,*.log}}'
{i}    ]
{i}}}
'''


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)exon_plot_min_bf[ \t]*=[ \t]*5[ \t]*$",
                    lambda m: m.group(0) + PARAMS.format(i=m.group("i"), m=MARKER), "params")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)withName: 'CNV_CONSENSUS_MULTI' \{[ \t]*$",
                    lambda m: PROCESS.format(i=m.group("i"), m=TAG) + m.group(0), "process block")
    notes.append(n)
    return t, notes


FILES = [
    ("bin/cnv_consensus_multi.py",           patch_consensus_py),
    ("modules/local/cnv_consensus_multi.nf", patch_consensus_nf),
    ("workflows/tspipe.nf",                  patch_tspipe),
    ("conf/twist_apply.config",              patch_twist_apply),
]


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
            new_text, notes = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        if rel.endswith(".py"):
            try:
                compile(new_text, path, "exec")
            except SyntaxError as exc:
                print("   [error] does not compile: %s" % exc); failed = True; continue
        b0, b1 = original.count("{") - original.count("}"), new_text.count("{") - new_text.count("}")
        print("   [check] markers %d (expected 1); brace balance %d/%d" % (new_text.count(MARKER), b0, b1))
        if new_text.count(MARKER) != 1 or b0 != b1:
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_hmf_purple_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
