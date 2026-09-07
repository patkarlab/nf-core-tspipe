# DASH_CNV_V1 -- CNV tab on the v2 outputs -- 2026-09-07

Reads clinical/cnv/ (ORG_CNV_V1) through bin/dashboard_builder/parsers/cnv_v2.py,
merged into ctx["cnv"] by build.py (never fatal). The CNV tab opens with:
  - one line: PURPLE status/purity/ploidy/sex (advisory badge when not trusted),
    sex check, consensus tier counts, blacklisted genes
  - consensus table (non-neutral genes; tiers; per-arm calls K G B P E H; LOO fp)
  - DECoN table (reportable + multi-exon calls at BF >= 5)
  - chromosome pages gallery (24 pages, report-selectable cards)
  - exon-level figures gallery
Legacy sections remain below a "Legacy CNV views" divider until 7b.

Files
    bin/dashboard_builder/parsers/cnv_v2.py
    tools/patches/2026-09-07/patch_dashboard_cnv_v2.py   build.py + sample_report.html.j2

Placement (repo root)
    cp <bundle>/bin/dashboard_builder/parsers/cnv_v2.py bin/dashboard_builder/parsers/
    cp <bundle>/tools/patches/2026-09-07/patch_dashboard_cnv_v2.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_dashboard_cnv_v2.py [--apply]

Rebuild: bin/ is not hashed by Nextflow, so a resume leaves DASHBOARD cached;
force it once with a throwaway config:
    printf "process { withName: 'DASHBOARD' { cache = false } }\n" > /tmp/dash_nocache.config
    nextflow run . ... -resume <session> -c conf/twist_apply.config -c /tmp/dash_nocache.config
