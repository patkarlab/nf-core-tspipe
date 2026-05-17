/*
 * subworkflows/local/annotation.nf
 *
 * Replaces scripts/13_annotate.py -> 14_variant_filter.py -> 17_variant_validator.py
 * -> 15_oncovi.py -> 17b_flt3_to_variants.py.
 *
 * Note the original step ordering: 14 -> 17 -> 15 -> 16 -> 16b -> 18 -> 19 -> 20
 * (the numbers reflect when scripts were ADDED, not when they execute).
 */

include { VEP_ANNOTATE        } from '../../modules/local/vep_annotate'
include { VARIANT_FILTER      } from '../../modules/local/variant_filter'
include { VARIANT_VALIDATOR   } from '../../modules/local/variant_validator'
include { ONCOVI              } from '../../modules/local/oncovi'
include { FLT3_TO_VARIANTS    } from '../../modules/local/flt3_to_variants'

workflow ANNOTATION {

    take:
        somaticseq_vcf_ch       // [meta, vcf]
        flt3_consensus_tsv_ch   // [meta, tsv]
        u2af1_tsv_ch            // [meta, tsv] (from U2AF1_RESCUE)
        blacklist_ch            // path or []
        reference_ch

    main:
        VEP_ANNOTATE(somaticseq_vcf_ch, reference_ch)

        // Join VEP output with U2AF1 rescue on meta.id. Both channels
        // emit one tuple per sample so this is 1:1. variant_filter.py
        // auto-discovers the staged u2af1 TSV by convention.
        ch_filter_in = VEP_ANNOTATE.out.tsv.join(u2af1_tsv_ch)
        VARIANT_FILTER(ch_filter_in, blacklist_ch)

        VARIANT_VALIDATOR(VARIANT_FILTER.out.clinical)

        ONCOVI(VARIANT_VALIDATOR.out.tsv)

        // 17b: merge FLT3 consensus into the clinical TSV (tag SNV-path hits
        // as Confirmed_by_FLT3_ITD_ensemble; append ITD rows that aren't already
        // represented).
        ch_to_merge = ONCOVI.out.tsv.join(flt3_consensus_tsv_ch)
        FLT3_TO_VARIANTS(ch_to_merge)

    emit:
        clinical_tsv = FLT3_TO_VARIANTS.out.tsv
}
