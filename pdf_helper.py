from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from PyPDF2 import PdfReader, PdfWriter
import io
import os

def create_watermark_pdf(text: str, fontsize: int = 36, color: str = 'white'):
    """
    Create a single-page PDF (as bytes) containing centered transparent text.
    We'll overlay this onto pages of the input PDF.
    """
    packet = io.BytesIO()
    # Use large page size; the merging will scale if needed.
    c = canvas.Canvas(packet)
    # transparent background; we'll set fill color based on requested color
    if color == 'black':
        fill = 0
    else:
        fill = 1
    # reportlab uses grayscale 0 black .. 1 white for setFillGray
    c.setFillGray(1 - fill)
    width, height = 612, 792  # default letter; merging will place based on mediaBox
    c.setFont("Helvetica-Bold", fontsize)
    # Draw centered
    text_width = c.stringWidth(text, "Helvetica-Bold", fontsize)
    x = (width - text_width) / 2
    y = height / 2
    c.drawString(x, y, text)
    c.save()
    packet.seek(0)
    return packet.read()

def add_watermark_to_pdf(input_pdf_path: str, output_pdf_path: str, text: str, fontsize: int = 36, color: str = 'white'):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    watermark_bytes = create_watermark_pdf(text, fontsize, color)
    wm_reader = PdfReader(io.BytesIO(watermark_bytes))
    watermark_page = wm_reader.pages[0]

    for page in reader.pages:
        # Merge watermark page onto existing page, centered.
        # PyPDF2's merge_page places overlay at same mediaBox; for better control we could use pdfrw or pikepdf.
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)
    return output_pdf_path
