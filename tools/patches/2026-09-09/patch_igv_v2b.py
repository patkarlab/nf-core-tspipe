#!/usr/bin/env python3
"""IGV_V2B -- pipeline half of the IGV block (D10, D11 data side, colour-by-strand).

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All-or-nothing;
.bak_IGV_V2B_<timestamp> backups. Changes the IGV_REPORTS module inputs and bin/igv_reports.py,
so a resume re-executes IGV_REPORTS (8) plus ORGANIZE_OUTPUT, DASHBOARD and REPORT_BUNDLE.

bin/igv_reports.py
  - --flt3-consensus <sample>_flt3_consensus.tsv: one IGV-report row per FLT3-ITD consensus
    event (chr13, POS = pos_hg38, REF from the FASTA, ALT = REF + inserted sequence, gene FLT3,
    consequence FLT3-ITD_<n>bp, HGVSp, mean VAF, tools as callers), independent of the
    SomaticSeq filters -- the ITD pathway is separate. <DUP> with END when the inserted
    sequence is unknown. De-duplicated against rows already present.
  - tracks are now declared through a --track-config JSON (igv-reports passes every key to
    igv.js): the alignment track defaults to colorBy "strand"; an annotation track
    (--gene-track, the panel exonwise BED for now, a GTF later) sits under the reads.
modules/local/igv_reports.nf
  - input tuple gains path(flt3_consensus); new value input path(gene_track).
workflows/tspipe.nf
  - IGV_REPORTS join adds ch_flt3_consensus; ch_igv_gene_track from params.igv_gene_track,
    falling back to params.exonwise_bed.
nextflow.config
  - params.igv_gene_track = null.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "IGV_V2B"
STAMP = time.strftime("%Y%m%d_%H%M%S")


class PatchError(Exception):
    pass


def read(path):
    if not os.path.isfile(path):
        raise PatchError("missing file: %s" % path)
    with open(path) as f:
        return f.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# bin/igv_reports.py
# ---------------------------------------------------------------------------
PY_ARGS_OLD = '''    parser.add_argument("--flanking", type=int, default=500,
                        help="Flanking region in bp (default: 500, matches production)")
    return parser.parse_args()
'''
PY_ARGS_NEW = '''    parser.add_argument("--flanking", type=int, default=500,
                        help="Flanking region in bp (default: 500, matches production)")
    # IGV_V2B
    parser.add_argument("--flt3-consensus", default=None,
                        help="<sample>_flt3_consensus.tsv; one report row per FLT3-ITD consensus event (IGV_V2B)")
    parser.add_argument("--gene-track", default=None,
                        help="annotation file (BED/GTF) drawn under the reads (IGV_V2B)")
    parser.add_argument("--gene-track-name", default="Exons (panel)",
                        help="display name of --gene-track (default: 'Exons (panel)')")
    parser.add_argument("--color-by", default="strand",
                        help="igv.js colorBy for the alignment track: strand (default), none, ...")
    return parser.parse_args()
'''

PY_FLT3_FUNC = '''

# IGV_V2B: FLT3-ITD consensus events as report rows. The ITD pathway (FLT3_ITD_EXT, filt3r,
# getITD, Pindel ensemble) is separate from SomaticSeq; a low-VAF ITD is often REJECT/LOW_CALLERS
# in the variant tables and would otherwise never get an IGV view.
FLT3_CHROM = "chr13"
FLT3_NEGATIVE = {"", "negative", "no_itd", "no-itd"}


def flt3_consensus_rows(path, fasta_path, sample):
    """Rows shaped like read_clinical_tsv() output, one per positive consensus event."""
    rows = []
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\\t")
        events = list(reader)
    if not events:
        return rows
    fasta = pysam.FastaFile(fasta_path)
    try:
        for ev in events:
            status = (ev.get("status") or "").strip().lower()
            if status in FLT3_NEGATIVE:
                continue
            try:
                pos = int(round(float(ev.get("pos_hg38") or "")))
            except ValueError:
                log.warning("IGV_V2B: FLT3 consensus event without a usable pos_hg38, skipped: %s", ev)
                continue
            ref = fasta.fetch(FLT3_CHROM, pos - 1, pos).upper()
            ins = (ev.get("inserted_seq") or "").strip().upper()
            try:
                length = int(round(float(ev.get("length_bp") or "0")))
            except ValueError:
                length = len(ins)
            row = {
                "Chr": FLT3_CHROM, "Start": str(pos), "Ref": ref,
                "Alt": (ref + ins) if ins else "<DUP>",
                "Gene": "FLT3",
                "Consequence": "FLT3-ITD_%dbp" % (length or len(ins)),
                "HGVSp": ev.get("hgvsp") or "",
                "VAF_pct": ev.get("vaf_pct_mean") or "",
                "Callers": ev.get("tools") or "",
                "rsID": "", "Filter": "PASS",
                "_flt3_end": str(pos + (length or len(ins))) if not ins else "",
            }
            rows.append(row)
    finally:
        fasta.close()
    log.info("IGV_V2B: %d FLT3-ITD consensus event(s) from %s", len(rows), path)
    return rows


def write_track_config(path, sample, vcf_path, bam_path, gene_track, gene_track_name, color_by):
    """igv-reports --track-config: every key other than url/format/type is passed to igv.js."""
    import json
    tracks_cfg = [
        {"url": os.path.abspath(vcf_path), "format": "vcf", "type": "variant",
         "name": os.path.basename(vcf_path).replace(".gz", "")},
        {"url": os.path.abspath(bam_path), "format": "bam", "type": "alignment",
         "name": os.path.basename(bam_path).replace(".bam", "")},
    ]
    if color_by and color_by.lower() != "none":
        tracks_cfg[1]["colorBy"] = color_by
    if gene_track:
        tracks_cfg.append({"url": os.path.abspath(gene_track), "type": "annotation",
                           "name": gene_track_name, "displayMode": "EXPANDED", "height": 70})
    with open(path, "w") as fh:
        json.dump(tracks_cfg, fh, indent=2)
    return path
'''

PY_HEADER_OLD = '''        '##INFO=<ID=Callers,Number=1,Type=String,Description="Variant callers">',
        "#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO",
'''
PY_HEADER_NEW = '''        '##INFO=<ID=Callers,Number=1,Type=String,Description="Variant callers">',
        '##INFO=<ID=END,Number=1,Type=Integer,Description="End position (IGV_V2B: FLT3-ITD without inserted sequence)">',
        '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Structural variant type">',
        '##ALT=<ID=DUP,Description="Duplication">',
        "#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO",
'''
PY_INFO_OLD = '''                    info_parts.append(f"{key}={val.replace(';', ',')}")
            info = ";".join(info_parts) if info_parts else "."
'''
PY_INFO_NEW = '''                    info_parts.append(f"{key}={val.replace(';', ',')}")
            if row.get("_flt3_end"):   # IGV_V2B: symbolic <DUP> needs END
                info_parts.append(f"END={row['_flt3_end']};SVTYPE=DUP")
            info = ";".join(info_parts) if info_parts else "."
'''
PY_MAIN_OLD = '''    if not rows:
        log.warning("No variants found -- skipping report generation")
'''
PY_MAIN_NEW = '''    # IGV_V2B (D11): FLT3-ITD consensus events, de-duplicated against rows already present
    if args.flt3_consensus and os.path.isfile(args.flt3_consensus):
        have = {(r["Chr"], r["Start"], r["Ref"], r["Alt"]) for r in rows}
        added = 0
        for r in flt3_consensus_rows(args.flt3_consensus, args.fasta, args.sample):
            key = (r["Chr"], r["Start"], r["Ref"], r["Alt"])
            if key not in have:
                have.add(key)
                rows.append(r)
                added += 1
        log.info("IGV_V2B: added %d FLT3-ITD row(s)", added)

    if not rows:
        log.warning("No variants found -- skipping report generation")
'''
PY_CMD_OLD = '''    cmd = [
        "create_report",
        vcf_path,
        "--fasta", args.fasta,
        "--tracks", vcf_path, args.bam,
        "--info-columns", "Gene", "Consequence", "HGVSp", "VAF_pct", "Callers",
'''
PY_CMD_NEW = '''    # IGV_V2B: tracks via --track-config so igv.js options (colorBy, annotation track) pass through
    track_cfg = write_track_config(os.path.join(outdir, f"{args.sample}.igv_tracks.json"), args.sample,
                                   vcf_path, args.bam, args.gene_track, args.gene_track_name, args.color_by)
    cmd = [
        "create_report",
        vcf_path,
        "--fasta", args.fasta,
        "--track-config", track_cfg,
        "--info-columns", "Gene", "Consequence", "HGVSp", "VAF_pct", "Callers",
'''


def patch_py(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, PY_ARGS_OLD, PY_ARGS_NEW, "igv_reports.py args")
    text = replace_once(text, "\n\ndef tsv_to_vcf(rows, vcf_gz_path):\n", PY_FLT3_FUNC + "\n\ndef tsv_to_vcf(rows, vcf_gz_path):\n", "igv_reports.py helpers")
    text = replace_once(text, PY_HEADER_OLD, PY_HEADER_NEW, "igv_reports.py VCF header")
    text = replace_once(text, PY_INFO_OLD, PY_INFO_NEW, "igv_reports.py INFO END")
    text = replace_once(text, PY_MAIN_OLD, PY_MAIN_NEW, "igv_reports.py main FLT3")
    text = replace_once(text, PY_CMD_OLD, PY_CMD_NEW, "igv_reports.py create_report cmd")
    return text, "patch"


# ---------------------------------------------------------------------------
# modules/local/igv_reports.nf
# ---------------------------------------------------------------------------
NF_IN_OLD = '''        tuple val(meta), path(clinical_tsv), path(bam), path(bai), path(filtered_tsv)   // SPIKEIN_V1d
        tuple path(fasta), path(fai), path(dict)
        path spikein_asset   // SPIKEIN_V1d: assets/<panel>/spikein_regions.tsv, or [] when the panel has none
'''
NF_IN_NEW = '''        tuple val(meta), path(clinical_tsv), path(bam), path(bai), path(filtered_tsv), path(flt3_consensus)   // SPIKEIN_V1d; IGV_V2B adds the FLT3 consensus
        tuple path(fasta), path(fai), path(dict)
        path spikein_asset   // SPIKEIN_V1d: assets/<panel>/spikein_regions.tsv, or [] when the panel has none
        path gene_track      // IGV_V2B: annotation track under the reads (params.igv_gene_track or the exonwise BED), or []
'''
NF_SCRIPT_OLD = '''        def spikein_args = spikein_asset ? "--extra-input ${filtered_tsv} --spikein-regions ${spikein_asset}" : ''   // SPIKEIN_V1d
        """
        igv_reports.py \\\\
            --sample  ${meta.id} \\\\
            --input   ${clinical_tsv} \\\\
            --bam     ${bam} \\\\
            --fasta   ${fasta} \\\\
            --output  ${meta.id}_igv_report.html \\\\
            ${spikein_args}
'''
NF_SCRIPT_NEW = '''        def spikein_args = spikein_asset ? "--extra-input ${filtered_tsv} --spikein-regions ${spikein_asset}" : ''   // SPIKEIN_V1d
        def gene_track_args = gene_track ? "--gene-track ${gene_track}" : ''   // IGV_V2B
        """
        igv_reports.py \\\\
            --sample  ${meta.id} \\\\
            --input   ${clinical_tsv} \\\\
            --bam     ${bam} \\\\
            --fasta   ${fasta} \\\\
            --output  ${meta.id}_igv_report.html \\\\
            --flt3-consensus ${flt3_consensus} \\\\
            ${gene_track_args} \\\\
            ${spikein_args}
'''


def patch_nf(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, NF_IN_OLD, NF_IN_NEW, "igv_reports.nf inputs")
    text = replace_once(text, NF_SCRIPT_OLD, NF_SCRIPT_NEW, "igv_reports.nf script")
    return text, "patch"


# ---------------------------------------------------------------------------
# workflows/tspipe.nf
# ---------------------------------------------------------------------------
WF_OLD = '''    IGV_REPORTS(
        ANNOTATION.out.clinical_tsv.join(PREPROCESSING.out.final_bam).join(ANNOTATION.out.filtered_tsv),   // SPIKEIN_V1d
        ch_reference,
        ch_igv_spikein
    )
'''
WF_NEW = '''    // IGV_V2B: FLT3 consensus rows in the report (the ITD pathway is separate from SomaticSeq) and an
    // annotation track under the reads: params.igv_gene_track, or the exonwise BED when unset.
    def igv_gene_track_path = params.igv_gene_track ?: params.exonwise_bed
    ch_igv_gene_track = Channel.value( igv_gene_track_path ? file(igv_gene_track_path, checkIfExists: true) : [] )
    IGV_REPORTS(
        ANNOTATION.out.clinical_tsv.join(PREPROCESSING.out.final_bam).join(ANNOTATION.out.filtered_tsv)   // SPIKEIN_V1d
            .join(ch_flt3_consensus),   // IGV_V2B
        ch_reference,
        ch_igv_spikein,
        ch_igv_gene_track
    )
'''


def patch_wf(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, WF_OLD, WF_NEW, "tspipe.nf IGV_REPORTS call"), "patch"


# ---------------------------------------------------------------------------
# nextflow.config
# ---------------------------------------------------------------------------
CFG_OLD = "    exonwise_bed       = null   // exon-collapsed BED for mosdepth only\n"
CFG_NEW = ("    exonwise_bed       = null   // exon-collapsed BED for mosdepth only\n"
           "    igv_gene_track     = null   // IGV_V2B: annotation track (BED/GTF) under the reads in the IGV report; exonwise_bed when unset\n")


def patch_cfg(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, CFG_OLD, CFG_NEW, "nextflow.config param"), "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        ("bin/igv_reports.py", patch_py),
        ("modules/local/igv_reports.nf", patch_nf),
        ("workflows/tspipe.nf", patch_wf),
        ("nextflow.config", patch_cfg),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
    except PatchError as e:
        print("[error] %s" % e)
        print("[error] nothing written")
        sys.exit(1)
    for path, _, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write")
        return
    for path, new, status in plan:
        if status == "skip":
            continue
        bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
        shutil.copy2(path, bak)
        print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
