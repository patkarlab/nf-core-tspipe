/*
 * subworkflows/local/sv_calling.nf
 *
 * Replaces scripts/11_sv_callers.py + 19_sv_annotate.py.
 */

include { SV_CALLERS  } from '../../modules/local/sv_callers'
include { SV_ANNOTATE } from '../../modules/local/sv_annotate'

workflow SV_CALLING {

    take:
        bam_ch
        reference_ch
        bed_ch

    main:
        SV_CALLERS(bam_ch, reference_ch, bed_ch)
        SV_ANNOTATE(SV_CALLERS.out.vcf)

    emit:
        annotated = SV_ANNOTATE.out.tsv
}
