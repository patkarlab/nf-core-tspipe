#!/usr/bin/env python3
"""
patch_containers_v1.py -- CONTAINERS_V1 (FREEZE A1, runtime switch; v1b = include path fixed, empty selector blocks removed)

Puts every HOST-class tspipe process on local/tspipe-host:v1 and removes the host-environment
plumbing the site configs carried:

  1. writes conf/containers.config: per-process `container` + `containerOptions --env PATH=...`
     (the env order each process had on gandalf), ext.* tool paths inside the image, and the
     params that name an environment or install (legacy_python_env, oncovi_dir, purecn_extdata,
     hmf_env, reconcnv_env, annovar_script, dashboard_python) pointed at /opt. PATH is set with
     --env because a beforeScript export never reaches a Docker container and, under
     Singularity/Apptainer, PATH is the one host variable that is not inherited.
  2. conf/gandalf.config: drops the global beforeScript PATH export, the env { } block of host
     env paths, the STRELKA / PLATYPUS / VARDICT host-path overrides, and includes containers.config.
  3. conf/twist_apply.config: drops every `container = null` and beforeScript PATH line (they
     existed for PoN version parity with the host cnvkit/GATK, which the image now carries), and
     repoints purecn_extdata / hmf_env / reconcnv_env at /opt (a -c overlay loads after the
     profile, so these literals would otherwise win).
  4. conf/modules.config: the BPT_.* block loses `conda = params.legacy_python_env` and
     `container = null` (BUILD_PON_TWIST runs on the same image).

Anchor-based, MARKER-guarded, dry-run by default; --apply writes .bak_containers_<stamp> copies.
Anchors were taken from the 2026-09-10 13:48 recon of conf/. Every `container` directive changes
the affected task hashes: the next run on the image re-executes all HOST-class processes.
"""

import argparse
import os
import re
import shutil
import sys
import time

MARKER = "MARKER CONTAINERS_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")

CONTAINERS_CONFIG = '''/*
 * conf/containers.config -- %(marker)s (FREEZE A1)
 *
 * Every process that ran on a gandalf conda environment now runs on local/tspipe-host:v1
 * (containers/tspipe-host/), which carries those environments unpacked at /opt/envs/<name>
 * and the external installs under /opt/. Included from every site profile; never load it
 * alone. Per-process PATH is set with --env (Docker, Singularity >= 3.6, Apptainer): a
 * beforeScript export does not reach a Docker container, and under Singularity PATH is the one
 * host variable that is not inherited. Order = what the process had on gandalf.
 */

def tspipe_host_image = 'local/tspipe-host:v1'
def tspipe_env_root   = '/opt/envs'
def tspipe_base_path  = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
def tspipe_env_path   = { List envs ->
    '--env PATH=' + envs.collect { tspipe_env_root + '/' + it + '/bin' }.join(':') + ':' + tspipe_base_path
}

params {
    // Environments and installs inside the image (the host defaults in nextflow.config /
    // gandalf.config are superseded here; twist_apply.config carries the same /opt values).
    legacy_python_env = "${tspipe_env_root}/targeted-seq"
    dashboard_python  = "${tspipe_env_root}/targeted-seq/bin/python"
    oncovi_dir        = '/opt/oncovi'
    annovar_script    = '/opt/annovar/table_annovar.pl'
    purecn_extdata    = "${tspipe_env_root}/purecn/lib/R/library/PureCN/extdata"
    hmf_env           = "${tspipe_env_root}/hmftools"
    reconcnv_env      = "${tspipe_env_root}/reconCNV"
}

process {
    // targeted-seq first: aligners, callers, GATK CNV, consensus, python tooling, host-side reporting
    withName: 'BWA_MEM|ABRA2|FREEBAYES|VARDICT|VARSCAN|PINDEL|VEP_ANNOTATE|VARIANT_FILTER|U2AF1_RESCUE|CNVKIT|GATK_CNV_.*|CNV_BAF_CNLOH|CNV_CONSENSUS_MULTI|DASHBOARD|REPORT_BUNDLE|RUN_BUNDLE|VARIANT_VALIDATOR|ONCOVI|FLT3_TO_VARIANTS|BPT_.*' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['targeted-seq'])
    }
    // py2 first: Strelka2 and Platypus
    withName: 'STRELKA|PLATYPUS' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['py2', 'targeted-seq'])
    }
    withName: 'STRELKA' {
        ext.python2     = 'python2'
        ext.strelka_bin = '/opt/strelka2/bin/configureStrelkaGermlineWorkflow.py'
    }
    withName: 'VARDICT' {
        ext.vardict_helpers_dir = '/opt/vardict/bin'
    }
    // PureCN (R), DECoN (R + python3), hmftools (Java 21 + python3), reconCNV (py3.6 bokeh + python3)
    withName: 'PURECN.*' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['purecn', 'targeted-seq'])
    }
    withName: 'DECON' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['decon', 'targeted-seq'])
    }
    withName: 'HMF_.*' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['hmftools', 'targeted-seq'])
    }
    withName: 'RECONCNV' {
        container        = tspipe_host_image
        containerOptions = tspipe_env_path(['reconCNV', 'targeted-seq'])
    }
}
''' % {"marker": MARKER}

# ---- gandalf.config anchors (verbatim from recon) --------------------------------------------
G_ENV_BLOCK = '''env {
    // The targeted-seq env already has fastp, bwa, samtools, gatk4, abra2,
    // cnvkit, freebayes, vardict, varscan, somaticseq, pysam, pandas, numpy.
    // Put it first on PATH so all module processes find these tools.
    TARGETED_SEQ_ENV   = '/home/hemat/anaconda3/envs/targeted-seq'
    // The py2 env for Strelka and Platypus.
    PY2_ENV            = '/home/hemat/anaconda3/envs/py2'
}

// Make the conda bin available inside every process
process {
    beforeScript = \'\'\'
        export PATH=/home/hemat/anaconda3/envs/targeted-seq/bin:$PATH
    \'\'\'

    withName: 'DEEPSOMATIC' {'''
G_ENV_BLOCK_NEW = '''// %s: host conda environments are no longer used; every HOST-class process runs on
// local/tspipe-host:v1 (conf/containers.config, included at the end of this file).
process {
    withName: 'DEEPSOMATIC' {''' % MARKER

G_STRELKA_BLOCK = '''    // Strelka and Platypus need the py2 env
    withName: 'STRELKA' {
        // Strelka2 needs python2 + the configureStrelkaGermlineWorkflow.py script
        ext.python2     = '/home/hemat/anaconda3/envs/py2/bin/python'
        ext.strelka_bin = '/goast/hemat_data/targeted-seq-pipeline/software/strelka2/bin/configureStrelkaGermlineWorkflow.py'
        // py2 env needs to be on PATH for strelka's internal subprocess calls too
        beforeScript    = 'export PATH=/home/hemat/anaconda3/envs/py2/bin:$PATH'
    }
    withName: 'PLATYPUS' {
        // Platypus is a py2 tool; conda wrapper handles invocation when py2/bin is on PATH first
        beforeScript = 'export PATH=/home/hemat/anaconda3/envs/py2/bin:$PATH'
    }

    // VarDict is a binary outside the conda env
    withName: 'VARDICT' {
        // teststrandbias.R and var2vcf_valid.pl ship inside the VarDictJava install
        ext.vardict_helpers_dir = '/goast/hemat_data/programs/VarDictJava/build/install/VarDict/bin'
    }

'''
G_STRELKA_BLOCK_NEW = '''    // %s: STRELKA / PLATYPUS / VARDICT tool paths come from conf/containers.config.

''' % MARKER

G_INCLUDE = '''
// %s: containers for every former host-env process (last, so it wins over the blocks above).
includeConfig 'containers.config'
''' % MARKER

# ---- twist_apply.config anchors ----------------------------------------------------------------
T_PARAMS_OLD = '''    purecn_extdata     = '/home/hemat/anaconda3/envs/purecn/lib/R/library/PureCN/extdata\''''
T_PARAMS_NEW = '''    purecn_extdata     = '/opt/envs/purecn/lib/R/library/PureCN/extdata'   // %s: inside local/tspipe-host''' % MARKER
T_HMF_OLD = '''    hmf_env           = '/home/hemat/anaconda3/envs/hmftools\''''
T_HMF_NEW = '''    hmf_env           = '/opt/envs/hmftools'   // %s''' % MARKER
T_RECON_OLD = '''    reconcnv_env      = '/home/hemat/anaconda3/envs/reconCNV\''''
T_RECON_NEW = '''    reconcnv_env      = '/opt/envs/reconCNV'   // %s''' % MARKER

# ---- modules.config anchor -----------------------------------------------------------------
M_BPT_OLD = '''    withName: 'BPT_.*' {
        conda     = params.legacy_python_env
        container = null
    }'''
M_BPT_NEW = '''    // %s: BPT_.* runtime (local/tspipe-host:v1) comes from conf/containers.config''' % MARKER

CONTAINER_NULL_RE = re.compile(r"^[ \t]*container[ \t]*=[ \t]*null[ \t]*\n", re.M)
BEFORESCRIPT_RE = re.compile(r"^[ \t]*beforeScript[ \t]*=[ \t]*'export PATH=/home/hemat/anaconda3/envs/[^'\n]*'[ \t]*\n", re.M)
# v1b: a selector left with no setting is rejected by Nextflow 25.10 ("Unknown config attribute"),
# so blocks emptied by the removals above become a comment line.
EMPTY_BLOCK_RE = re.compile(r"^[ \t]*withName:[ \t]*'([^']+)'[ \t]*\{[ \t]*\n(?:[ \t]*\n)*[ \t]*\}[ \t]*\n", re.M)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit("[error] anchor '%s' matches %d times (expected 1)" % (label, n))
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    R = args.repo
    paths = {k: os.path.join(R, "conf", k + ".config") for k in ("gandalf", "twist_apply", "modules")}
    containers_path = os.path.join(R, "conf", "containers.config")
    texts = {k: read(p) for k, p in paths.items()}
    if any(MARKER in t for t in texts.values()) or os.path.exists(containers_path):
        print("[skip] %s already applied (marker present or conf/containers.config exists)" % MARKER)
        return 0

    g = texts["gandalf"]
    g = replace_once(g, G_ENV_BLOCK, G_ENV_BLOCK_NEW, "gandalf env+beforeScript block")
    g = replace_once(g, G_STRELKA_BLOCK, G_STRELKA_BLOCK_NEW, "gandalf STRELKA/PLATYPUS/VARDICT block")
    g = g.rstrip("\n") + "\n" + G_INCLUDE

    t = texts["twist_apply"]
    n_null = len(CONTAINER_NULL_RE.findall(t))
    n_bs = len(BEFORESCRIPT_RE.findall(t))
    if (n_null, n_bs) != (8, 4):
        raise SystemExit("[error] twist_apply.config: found %d 'container = null' and %d beforeScript lines (expected 8 and 4)" % (n_null, n_bs))
    t = CONTAINER_NULL_RE.sub("", t)
    t = BEFORESCRIPT_RE.sub("", t)
    emptied = EMPTY_BLOCK_RE.findall(t)
    t = EMPTY_BLOCK_RE.sub(lambda m: "    // %s: '%s' runtime comes from conf/containers.config\n" % (MARKER, m.group(1)), t)
    print("[plan] twist_apply.config: emptied selectors replaced by a comment: %s" % emptied)
    t = replace_once(t, T_PARAMS_OLD, T_PARAMS_NEW, "twist_apply purecn_extdata")
    t = replace_once(t, T_HMF_OLD, T_HMF_NEW, "twist_apply hmf_env")
    t = replace_once(t, T_RECON_OLD, T_RECON_NEW, "twist_apply reconcnv_env")

    m = texts["modules"]
    m = replace_once(m, M_BPT_OLD, M_BPT_NEW, "modules BPT_ block")

    new_texts = {"gandalf": g, "twist_apply": t, "modules": m}
    for k in new_texts:
        print("[plan] conf/%s.config: %+d lines" % (k, new_texts[k].count("\n") - texts[k].count("\n")))
    print("[plan] conf/containers.config: new, %d lines" % CONTAINERS_CONFIG.count("\n"))
    if not args.apply:
        print("[dry-run] no files written; re-run with --apply")
        return 0
    for k, p in paths.items():
        bak = p + ".bak_containers_" + STAMP
        shutil.copy2(p, bak)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(new_texts[k])
        print("[patch] %s (backup %s)" % (p, os.path.basename(bak)))
    with open(containers_path, "w", encoding="utf-8") as fh:
        fh.write(CONTAINERS_CONFIG)
    print("[write] %s" % containers_path)
    for k, p in paths.items():
        txt = read(p)
        if txt.count("{") != txt.count("}"):
            print("[WARN] brace imbalance in %s: { %d vs } %d" % (p, txt.count("{"), txt.count("}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
