# dashboard_builder v0.5.1 — layout fixes, CAVA on every card (DASH_LAYOUT_V1, 2026-09-09)

## What changed

- Every variant card (Clinical and All-filtered browsers) carries a CAVA line: MANE 1.5
  RefSeq transcript, CAVA HGVSc and HGVSp, with the CSN in the tooltip. Cards without a
  CAVA annotation say so. Previously CAVA was visible only in the expanded detail view,
  as the card nomenclature when VariantValidator had no result, and as the "CAVA differs"
  badge.
- MNV badge on the card and an "MNV note" row in the detail view when MNV_MERGE tagged the
  record (D17a).
- The Reporting snapshot now uses the same nomenclature preference as the cards
  (VariantValidator, then CAVA, then VEP); it previously skipped CAVA. Snapshots already
  stored in the browser keep their old strings until the variant is re-included.
- Left sidebar stays in view while scrolling (D1).
- Long insertions, COSMIC lists and caller lists wrap inside their cell instead of widening
  the page; Reporting tables use fixed column widths and every cell wraps (D5, D12).
- Tier field on the Reporting page grows with its text instead of clipping at 16 characters;
  Enter commits the value (D4).

## Verification

Nocache DASHBOARD/REPORT_BUNDLE re-render on run8; visual check on 26CGH60 and 26CGH1292.
