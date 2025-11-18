import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os


def extract_text_from_pdf(filepath: str) -> str:
    """Extrai texto do PDF usando PyMuPDF"""
    text = ""
    with fitz.open(filepath) as pdf:
        for page in pdf:
            text += page.get_text("text")
    return text


def split_pdf(filepath: str, pages: str) -> str:
    """Divide o PDF nas páginas indicadas (ex: '1-3,5,7-8')"""
    reader = PdfReader(filepath)
    writer = PdfWriter()
    page_ranges = []

    for part in pages.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            page_ranges.extend(range(start, end + 1))
        else:
            page_ranges.append(int(part))

    for i in page_ranges:
        writer.add_page(reader.pages[i - 1])

    output_path = filepath.replace(".pdf", "_split.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def merge_pdfs(filepaths: list) -> str:
    """Mescla múltiplos PDFs em um único arquivo"""
    merger = PdfMerger()
    for path in filepaths:
        merger.append(path)
    output = "static/uploads/merged.pdf"
    merger.write(output)
    merger.close()
    return output


def rotate_pdf(filepath: str, degrees: int = 90) -> str:
    """Rotaciona todas as páginas de um PDF"""
    reader = PdfReader(filepath)
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(degrees)
        writer.add_page(page)
    output_path = filepath.replace(".pdf", f"_rotated{degrees}.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def add_watermark(filepath: str, watermark_text: str) -> str:
    """Adiciona uma marca d'água de texto no PDF"""
    watermark_path = "static/uploads/_watermark.pdf"
    c = canvas.Canvas(watermark_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 36)
    c.setFillGray(0.5, 0.3)
    c.saveState()
    c.translate(300, 500)
    c.rotate(45)
    c.drawCentredString(0, 0, watermark_text)
    c.restoreState()
    c.save()

    reader = PdfReader(filepath)
    watermark = PdfReader(watermark_path).pages[0]
    writer = PdfWriter()

    for page in reader.pages:
        page.merge_page(watermark)
        writer.add_page(page)

    output_path = filepath.replace(".pdf", "_watermarked.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def protect_pdf(filepath: str, password: str) -> str:
    """Adiciona senha a um PDF"""
    reader = PdfReader(filepath)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(password)
    output_path = filepath.replace(".pdf", "_protected.pdf")
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
