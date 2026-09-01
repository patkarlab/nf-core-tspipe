/*
 * modules/local/bpt_check_samplesheet.nf
 *
 * Validates the BUILD_PON_TWIST samplesheet and emits a normalised copy
 * with a resolved `bai` column. FASTQ rows are accepted by the schema but
 * hard-fail in scaffold v1 (PREPROCESSING wiring is a follow-up).
 *
 * No conda/container directives here by design: the BPT_.* umbrella in
 * conf/modules.config supplies the host conda env and neutralises
 * container inheritance (2026-08-31 lesson).
 */

process BPT_CHECK_SAMPLESHEET {
    tag   "samplesheet"
    label 'process_single'

    input:
        path sheet

    output:
        path 'samplesheet.validated.csv', emit: csv

    stub:
        """
        # Populated stub so -stub-run exercises the full DAG: two included
        # males (stratum path) and one excluded female (gate path). Dummy
        # files are created locally so downstream input staging succeeds.
        mkdir -p stub_bams
        for s in StubMale1 StubMale2 StubFemale1; do
            touch stub_bams/\${s}.bam stub_bams/\${s}.bam.bai
        done
        {
            printf 'sample,sex,bam,bai,include_in_pon,note\\n'
            printf 'StubMale1,male,%s/stub_bams/StubMale1.bam,%s/stub_bams/StubMale1.bam.bai,true,\\n'     "\$PWD" "\$PWD"
            printf 'StubMale2,male,%s/stub_bams/StubMale2.bam,%s/stub_bams/StubMale2.bam.bai,true,\\n'     "\$PWD" "\$PWD"
            printf 'StubFemale1,female,%s/stub_bams/StubFemale1.bam,%s/stub_bams/StubFemale1.bam.bai,false,stub\\n' "\$PWD" "\$PWD"
        } > samplesheet.validated.csv
        """

    script:
        """
        bpt_check_samplesheet.py \\
            --input ${sheet} \\
            --output samplesheet.validated.csv
        """
}
