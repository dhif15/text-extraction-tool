import os
import shutil
import tempfile
import subprocess
from flask import Flask, request, render_template, send_file, redirect, url_for, session, jsonify
from pdf2image import convert_from_path
from pytesseract import image_to_string
from docx import Document
from PyPDF2 import PdfMerger
import locale
import pytesseract
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set up Tesseract and tessdata paths
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")  # Adjusted for local use
os.environ["TESSDATA_PREFIX"] = os.getenv("TESSDATA_PREFIX", os.path.join(os.getcwd(), "tessdata"))

# Flask App Initialization
app = Flask(__name__)
app.secret_key = "secret_key"

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


def convert_word_to_pdf(input_word_path, output_folder):
    """Convert Word document to PDF using LibreOffice CLI."""
    # libreoffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe" if os.name == 'nt' else "libreoffice"
    libreoffice_path = "/app/.apt/usr/bin/soffice" if os.name != 'nt' else "C:\\Program Files\\LibreOffice\\program\\soffice.exe"

    try:
        subprocess.run([
            libreoffice_path,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_folder,
            input_word_path
        ], check=True)
        # استخراج اسم ملف PDF الناتج
        base_name = os.path.splitext(os.path.basename(input_word_path))[0]
        return os.path.join(output_folder, f"{base_name}.pdf")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error converting Word to PDF: {e}")
        raise RuntimeError(f"Error converting Word to PDF: {e}")


def convert_images_to_pdf(image_paths, output_pdf_path):
    """Combine multiple images into a single PDF."""
    merger = PdfMerger()
    for image_path in image_paths:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        merger.append(image_path)
    with open(output_pdf_path, "wb") as f:
        merger.write(f)


def convert_pdf_to_images(input_pdf_path, output_folder, first_page=None, last_page=None):
    """Convert each page of a PDF to images."""
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF file not found: {input_pdf_path}")

    images = convert_from_path(
        input_pdf_path, dpi=300, first_page=first_page, last_page=last_page
    )
    image_paths = []
    for i, image in enumerate(images):
        output_path = os.path.join(output_folder, f"page_{i + 1}.png")
        image.save(output_path, "PNG")
        image_paths.append(output_path)
    return image_paths


def extract_text_from_images(image_paths, language="ara"):
    extracted_text = ""
    for image_path in image_paths:
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            extracted_text += image_to_string(image_path, lang=language)
        except Exception as e:
            logging.error(f"Error extracting text from {image_path}: {e}")
    return extracted_text


@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        reset_session()

        files = request.files.getlist("file")
        if not files:
            return jsonify({"error": "No files uploaded"}), 400
        try:
            temp_folder = tempfile.mkdtemp()
            uploaded_paths = []
            for file in files:
                file_path = os.path.join(temp_folder, file.filename)
                file.save(file_path)
                uploaded_paths.append(file_path)
            session["uploaded_file_paths"] = uploaded_paths
            return jsonify({"redirect": url_for("process")}), 200
        except Exception as e:
            logging.error(f"Error during upload: {e}")
            return jsonify({"error": str(e)}), 500
    return render_template("index.html")


@app.route("/process", methods=["GET"])
def process():
    file_paths = session.get("uploaded_file_paths")
    if not file_paths or not all(os.path.exists(path) for path in file_paths):
        return "Files not found", 404

    result_docx_path = session.get("result_docx")
    if not result_docx_path:
        try:
            output_folder = tempfile.mkdtemp()

            # Handle Images
            if len(file_paths) == 1 and file_paths[0].lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image_paths = [file_paths[0]]  # Single image
            elif len(file_paths) > 1 and all(path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")) for path in file_paths):
                combined_pdf_path = os.path.join(output_folder, "combined.pdf")
                convert_images_to_pdf(file_paths, combined_pdf_path)
                image_paths = convert_pdf_to_images(combined_pdf_path, output_folder)

            # Handle PDF Files
            elif file_paths[0].lower().endswith(".pdf"):
                image_paths = convert_pdf_to_images(file_paths[0], output_folder)

            # Handle Word Documents
            elif file_paths[0].lower().endswith(".docx"):
                pdf_path = convert_word_to_pdf(file_paths[0], output_folder)
                image_paths = convert_pdf_to_images(pdf_path, output_folder)

            # Unsupported File Types
            else:
                return "Unsupported file type.", 400

            # Extract text from images
            extracted_text = extract_text_from_images(image_paths)
            result_docx_path = os.path.join(output_folder, "extracted_text.docx")
            doc = Document()
            for line in extracted_text.splitlines():
                doc.add_paragraph(line)
            doc.save(result_docx_path)

            session["result_docx"] = result_docx_path
        except Exception as e:
            logging.error(f"Error during processing: {e}")
            return "An error occurred during processing.", 500
    return redirect(url_for("result"))


@app.route("/result")
def result():
    return render_template("result.html")


@app.route("/download")
def download_result():
    result_docx = session.get("result_docx")
    if not result_docx or not os.path.exists(result_docx):
        return "File not found", 404
    return send_file(result_docx, as_attachment=True)


@app.route("/reset")
def reset():
    reset_session()
    return redirect(url_for("upload"))


def reset_session():
    file_paths = session.pop("uploaded_file_paths", [])
    result_docx = session.pop("result_docx", None)

    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)

    if result_docx and os.path.exists(result_docx):
        shutil.rmtree(os.path.dirname(result_docx), ignore_errors=True)


if __name__ == "__main__":
    app.run(debug=True)
