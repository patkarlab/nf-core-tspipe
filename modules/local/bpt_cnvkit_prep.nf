/*
 * modules/local/bpt_cnvkit_prep.nf
 *
 * CNVkit target preparation from the single shared artifact
 * panel.combined.filtered.bed. The BED is already FAI-sorted with
 * contiguous chromosomes; it is never re-sorted here.
 *
 * Antitargets: 'empty' (default) writes a zero-length antitarget BED.
 * The in-panel CNV backbone already provides genome-wide bins, so
 * off-target bins add nothing. 'auto' is intentionally unimplemented in
 * v1 and fails loudly (module-review item).
 */

process BPT_CNVKIT_PREP {
    tag   "cnvkit_prep"
    label 'process_low'

    input:
        path bed

    output:
        path 'targets.split.bed', emit: targets
        path 'antitargets.bed',   emit: antitargets

    stub:
        """
        touch targets.split.bed antitargets.bed
        """

    script:
        def extra = task.ext.args ?: ''
        """
        cnvkit.py target ${bed} --split ${extra} -o targets.split.bed
        n=\$(wc -l < targets.split.bed)
        echo "[ok] targets.split.bed rows: \$n (source: ${bed})"
        if [ "\$n" -lt 1000 ]; then
            echo "[error] implausibly few target rows (\$n) from ${bed}" >&2
            exit 1
        fi

        if [ "${params.pon_antitarget}" = "empty" ]; then
            : > antitargets.bed
            echo "[ok] antitargets: empty by design (in-panel backbone provides genome-wide bins)"
        else
            echo "[error] pon_antitarget='${params.pon_antitarget}' not implemented in scaffold v1 (review item)" >&2
            exit 1
        fi
        """
}
