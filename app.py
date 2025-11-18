import os
from io import BytesIO
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    send_file, jsonify
)
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import fitz  # PyMuPDF para exportar página como PNG
import shutil

from dotenv import load_dotenv

# -------------------------------------------------
# CONFIGURAÇÃO BÁSICA
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Em desenvolvimento, carregamos variáveis do .env.
# Em produção (Render / Railway / etc.), as variáveis
# virão do painel da plataforma, então o .env nem é usado.
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Lê a API KEY do TinyMCE
TINYMCE_API_KEY = os.getenv("TINYMCE_API_KEY", "no-api-key")


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------------------------------------
# ROTAS PRINCIPAIS
# -------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file or file.filename == "":
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    # cria um alias "current" para sempre reabrir o último nome
    current_name = filename.replace(".pdf", "__current.pdf")
    current_path = os.path.join(app.config["UPLOAD_FOLDER"], current_name)
    shutil.copy2(save_path, current_path)

    return redirect(url_for("painel", filename=current_name))


@app.route("/painel")
def painel():
    filename = request.args.get("filename")
    if not filename:
        return redirect(url_for("index"))

    return render_template(
        "painel.html",
        filename=filename,
        tinymce_key=TINYMCE_API_KEY
    )


@app.route("/view/<path:filename>")
def view_pdf(filename):
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(pdf_path, mimetype="application/pdf")


@app.route("/download/<path:filename>")
def download_file(filename):
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(pdf_path, as_attachment=True, download_name=filename)


# -------------------------------------------------
# API – FERRAMENTAS DO PAINEL
# -------------------------------------------------
@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    filename = request.form.get("filename")
    degrees = int(request.form.get("degrees", "90"))

    src_path = os.path.join(UPLOAD_FOLDER, filename)
    reader = PdfReader(src_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(degrees)
        writer.add_page(page)

    out_pdf = BytesIO()
    writer.write(out_pdf)
    out_pdf.seek(0)

    with open(src_path, "wb") as f:
        f.write(out_pdf.read())

    return jsonify(ok=True, msg="Rotacionado.")


@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    filename = request.form.get("filename")
    text = request.form.get("text", "PDF Wizard")

    src_path = os.path.join(UPLOAD_FOLDER, filename)
    reader = PdfReader(src_path)
    writer = PdfWriter()

    # cria um PDF com a marca
    wm_stream = BytesIO()
    c = canvas.Canvas(wm_stream, pagesize=letter)
    c.setFont("Helvetica-Bold", 42)
    c.setFillGray(0.5, 0.3)
    c.saveState()
    c.translate(300, 400)
    c.rotate(30)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    wm_stream.seek(0)

    wm_pdf = PdfReader(wm_stream)
    wm_page = wm_pdf.pages[0]

    for page in reader.pages:
        page.merge_page(wm_page)
        writer.add_page(page)

    out_pdf = BytesIO()
    writer.write(out_pdf)
    out_pdf.seek(0)
    with open(src_path, "wb") as f:
        f.write(out_pdf.read())

    return jsonify(ok=True, msg="Marca d'água aplicada.")


@app.route("/api/page_png", methods=["POST"])
def api_page_png():
    filename = request.form.get("filename")
    page_index = int(request.form.get("page", "1")) - 1

    src_path = os.path.join(UPLOAD_FOLDER, filename)
    doc = fitz.open(src_path)

    if page_index < 0 or page_index >= len(doc):
        return jsonify(ok=False, msg="Página inválida.")

    page = doc[page_index]
    pix = page.get_pixmap(dpi=180)
    out = BytesIO()
    out.write(pix.tobytes("png"))
    out.seek(0)
    download_name = f"{os.path.splitext(filename)[0]}_p{page_index+1}.png"
    return send_file(out, mimetype="image/png", as_attachment=True, download_name=download_name)


@app.route("/api/insert_image", methods=["POST"])
def api_insert_image():
    filename = request.form.get("filename")
    page_index = int(request.form.get("page", "1")) - 1
    x = float(request.form.get("x", "50"))
    y = float(request.form.get("y", "50"))
    w = float(request.form.get("w", "200"))
    img = request.files.get("image")

    if not img:
        return jsonify(ok=False, msg="Nenhuma imagem enviada.")

    src_path = os.path.join(UPLOAD_FOLDER, filename)
    doc = fitz.open(src_path)

    if page_index < 0 or page_index >= len(doc):
        return jsonify(ok=False, msg="Página inválida.")

    page = doc[page_index]

    # carrega a imagem recebida
    img_bytes = img.read()
    img_pil = Image.open(BytesIO(img_bytes))
    img_stream = BytesIO()
    img_pil.save(img_stream, format="PNG")
    img_stream.seek(0)

    # coloca a imagem na página
    rect = fitz.Rect(x, y, x + w, y + (w * 0.6))
    page.insert_image(rect, stream=img_stream.getvalue())

    # salva no mesmo arquivo (sobrescrevendo com segurança)
    tmp = src_path + ".tmp"
    doc.save(tmp)
    doc.close()
    os.replace(tmp, src_path)

    return jsonify(ok=True, msg="Imagem inserida.")


@app.route("/api/merge", methods=["POST"])
def api_merge():
    filename = request.form.get("filename")
    files = request.files.getlist("files")

    src_path = os.path.join(UPLOAD_FOLDER, filename)
    base = fitz.open(src_path)
    for f in files:
        if f and allowed_file(f.filename):
            d = fitz.open(stream=f.read(), filetype="pdf")
            base.insert_pdf(d)
            d.close()

    tmp = src_path + ".tmp"
    base.save(tmp)
    base.close()
    os.replace(tmp, src_path)

    return jsonify(ok=True, msg="Mesclado com sucesso.")


@app.route("/api/extract_text", methods=["POST"])
def api_extract_text():
    filename = request.form.get("filename")
    src_path = os.path.join(UPLOAD_FOLDER, filename)

    doc = fitz.open(src_path)
    parts = []
    for i, page in enumerate(doc):
        parts.append(f"// Página {i+1}\n")
        parts.append(page.get_text())
        parts.append("\n\n")
    doc.close()

    return jsonify(ok=True, text="".join(parts))


# -------------------------------------------------
# ENTRADA LOCAL
# -------------------------------------------------
if __name__ == "__main__":
    # Em produção (gunicorn), esse bloco NÃO roda.
    # Aqui é só pra rodar localmente.
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
