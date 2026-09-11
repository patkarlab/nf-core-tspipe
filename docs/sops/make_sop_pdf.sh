#!/usr/bin/env bash
# make_sop_pdf.sh -- render SOP-TSPIPE-001.md to a controlled PDF.
#
# Markdown viewers and generic converters let wide tables and long paths run past the page
# margin. This renders through wkhtmltopdf with a print stylesheet that fixes table layout and
# wraps cell text, then stamps a document footer with page numbers (this wkhtmltopdf build
# ignores its own --footer-* options).
#
# Requires: python3 with the markdown, pypdf and reportlab packages; wkhtmltopdf.
# Usage: bash make_sop_pdf.sh docs/sops/SOP-TSPIPE-001.md docs/sops/SOP-TSPIPE-001.pdf
set -euo pipefail
SRC=${1:?source markdown}
OUT=${2:?output pdf}
CSS=$(dirname "$0")/sop_print.css
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python3 - "$SRC" "$TMP/body.html" <<'PY'
import sys, markdown
src = open(sys.argv[1]).read()
html = markdown.markdown(src, extensions=['tables', 'fenced_code', 'sane_lists'])
open(sys.argv[2], 'w').write(
    '<html><head><meta charset="utf-8"><title>SOP-TSPIPE-001</title></head><body>'
    + html + '</body></html>')
PY
wkhtmltopdf --quiet --enable-local-file-access --user-style-sheet "$CSS" \
    --page-size A4 --margin-top 16mm --margin-bottom 18mm --margin-left 14mm --margin-right 14mm \
    "$TMP/body.html" "$TMP/nofooter.pdf" 2>/dev/null || true
python3 - "$TMP/nofooter.pdf" "$OUT" <<'PY'
import sys, io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
src = PdfReader(sys.argv[1]); n = len(src.pages); out = PdfWriter()
for i, page in enumerate(src.pages, start=1):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 7); c.setFillGray(0.35)
    c.drawString(40, 24, "SOP-TSPIPE-001 v1.0  |  nf-core-tspipe v1.0.0")
    c.drawRightString(A4[0] - 40, 24, "Page %d of %d" % (i, n))
    c.setStrokeGray(0.75); c.setLineWidth(0.4); c.line(40, 32, A4[0] - 40, 32)
    c.save(); buf.seek(0)
    page.merge_page(PdfReader(buf).pages[0]); out.add_page(page)
with open(sys.argv[2], "wb") as fh: out.write(fh)
print("wrote %s (%d pages)" % (sys.argv[2], n))
PY
