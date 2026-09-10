#!/usr/bin/env bash
# containers/tspipe-host/smoke_test.sh -- run INSIDE local/tspipe-host:v1 (build.sh does it).
# Each check calls the tool a tspipe process calls, with the PATH that process will get, and
# prints a version. Any failure exits non-zero.
set -uo pipefail
R=${TSPIPE_ENV_ROOT:-/opt/envs}
fail=0
check() {
    local name="$1"; shift
    local out
    if out=$("$@" 2>&1); then
        printf "[ok]   %-28s %s\n" "$name" "$(echo "$out" | grep -v '^\s*$' | head -1 | cut -c1-90)"
    else
        printf "[FAIL] %-28s %s\n" "$name" "$(echo "$out" | tail -1 | cut -c1-120)"; fail=1
    fi
}
export PATH=$R/targeted-seq/bin:$PATH
check "python (targeted-seq)"   python --version
check "pandas/jinja2/pysam"     python -c "import pandas, jinja2, pysam, numpy, scipy; print(pandas.__version__, jinja2.__version__, pysam.__version__)"
check "bwa-mem2"                bash -c "bwa-mem2 version"
check "samtools"                bash -c "samtools --version | head -1"
check "bcftools"                bash -c "bcftools --version | head -1"
check "gatk 4.6.2.0"            bash -c "gatk --version 2>&1 | grep -i 'genome analysis' | head -1"
check "cnvkit.py"               bash -c "cnvkit.py version"
check "abra2"                   bash -c "abra2 2>&1 | grep -io 'ABRA2 version [^ ]*' | head -1"
check "freebayes"               bash -c "freebayes --version"
check "vardict-java"            bash -c "vardict-java 2>&1 | grep -io 'vardict_v[^ ]*' | head -1"
check "varscan"                 bash -c "varscan 2>&1 | grep -io 'VarScan v[0-9.]*' | head -1"
check "pindel"                  bash -c "pindel 2>&1 | grep -io 'Pindel version [^ ]*' | head -1"
check "R (targeted-seq)"        bash -c "R --version | head -1"
check "vardict helpers"         bash -c "ls /opt/vardict/bin/teststrandbias.R /opt/vardict/bin/var2vcf_valid.pl"
check "annovar table_annovar"   bash -c "perl /opt/annovar/table_annovar.pl 2>&1 | head -1"
check "oncovi dir"              bash -c "ls /opt/oncovi | head -3 | tr '\n' ' '"
check "vep 105"                 bash -c "PATH=$R/vep/bin:\$PATH $R/vep/bin/vep --help 2>&1 | grep -iE 'ensembl-vep|version' | head -1"
check "vep perl"                bash -c "$R/vep/bin/perl -e 'print \$^V'"
check "python2 (py2)"           bash -c "PATH=$R/py2/bin:\$PATH python2 --version"
check "strelka2 configure"      bash -c "PATH=$R/py2/bin:\$PATH python2 /opt/strelka2/bin/configureStrelkaGermlineWorkflow.py --version"
check "platypus"                bash -c "PATH=$R/py2/bin:\$PATH platypus callVariants --help 2>&1 | head -1"
check "PureCN 2.16"             bash -c "PATH=$R/purecn/bin:\$PATH Rscript -e 'suppressMessages(library(PureCN)); cat(as.character(packageVersion(\"PureCN\")))'"
check "PureCN extdata"          bash -c "ls $R/purecn/lib/R/library/PureCN/extdata/PureCN.R $R/purecn/lib/R/library/PureCN/extdata/Coverage.R"
check "ExomeDepth (decon)"      bash -c "PATH=$R/decon/bin:\$PATH Rscript -e 'suppressMessages(library(ExomeDepth)); cat(as.character(packageVersion(\"ExomeDepth\")))'"
check "java 21 (hmftools)"      bash -c "PATH=$R/hmftools/bin:\$PATH java -version 2>&1 | head -1"
check "hmftools jars"           bash -c "ls $R/hmftools/share/hmftools-amber-*/amber.jar $R/hmftools/share/hmftools-cobalt-*/cobalt.jar $R/hmftools/share/hmftools-purple-*/purple.jar | wc -l"
check "bokeh (reconCNV)"        bash -c "PATH=$R/reconCNV/bin:\$PATH python -c 'import bokeh; print(bokeh.__version__)'"
check "locale"                  bash -c "locale 2>&1 | grep -E '^LANG=' | head -1"
check "mplconfig writable"      bash -c "touch \$MPLCONFIGDIR/.probe && rm \$MPLCONFIGDIR/.probe && echo writable"
exit $fail
