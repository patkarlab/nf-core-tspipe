/*
 * modules/local/bpt_tool_versions.nf
 *
 * Records the exact tool versions used for this PoN build into
 * references/twist_myeloid/build_versions.txt. The PoN must be applied
 * with the same cnvkit/GATK versions (handoff invariant: 0.9.12 /
 * 4.6.2.0 matched across gandalf and clinical-23); this file is the
 * build-side half of that check.
 */

process BPT_TOOL_VERSIONS {
    tag   "versions"
    label 'process_single'

    output:
        path 'build_versions.txt', emit: versions

    stub:
        """
        touch build_versions.txt
        """

    script:
        """
        {
            echo "BUILD_PON_TWIST tool versions"
            echo "date: \$(date '+%Y-%m-%d %H:%M:%S %z')"
            echo "host: \$(hostname)"
            echo "python: \$(which python) (\$(python --version 2>&1))"
            echo "cnvkit: \$(cnvkit.py version 2>&1)"
            echo "gatk:"
            gatk --version 2>&1 | sed 's/^/    /'
            echo "mosdepth: \$(mosdepth --version 2>&1)"
            echo "samtools: \$(samtools --version 2>&1 | head -1)"
        } > build_versions.txt
        cat build_versions.txt
        """
}
