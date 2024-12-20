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

# Set up Tesseract and tessdata paths for Heroku
pytesseract.pytesseract.tesseract_cmd = "/app/.apt/usr/bin/tesseract"  # Path to Tesseract in Heroku
os.environ["TESSDATA_PREFIX"] = "/app/tessdata"  # Path to the tessdata directory

# Flask App Initialization
app = Flask(__name__)
app.secret_key = "secret_key"

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


def simplify_path(path):
    return os.path.normpath(path)


def convert_word_to_pdf(input_word_path, output_pdf_path):
    """Convert Word document to PDF using LibreOffice CLI."""
    try:
        subprocess.run([
            "libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
            os.path.dirname(output_pdf_path), input_word_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error converting Word to PDF: {e}")


def convert_images_to_pdf(image_paths, output_pdf_path):
    """Combine multiple images into a single PDF."""
    merger = PdfMerger()
    for image_path in image_paths:
        merger.append(image_path)
    with open(output_pdf_path, "wb") as f:
        merger.write(f)


def convert_pdf_to_images(input_pdf_path, output_folder, first_page=None, last_page=None):
    """Convert each page of a PDF to images."""
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
        extracted_text += image_to_string(image_path, lang=language)
    return extracted_text


@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        # Clear previous session data
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
            combined_pdf_path = os.path.join(output_folder, "combined.pdf")

            if len(file_paths) > 1 and all(path.lower().endswith((".png", ".jpg", ".jpeg")) for path in file_paths):
                # Combine images into a single PDF
                convert_images_to_pdf(file_paths, combined_pdf_path)
                image_paths = convert_pdf_to_images(combined_pdf_path, output_folder)
            elif file_paths[0].endswith(".pdf"):
                # Process all pages of the PDF
                image_paths = convert_pdf_to_images(file_paths[0], output_folder)
            elif file_paths[0].endswith(".docx"):
                pdf_path = os.path.join(output_folder, "temp.pdf")
                convert_word_to_pdf(file_paths[0], pdf_path)
                image_paths = convert_pdf_to_images(pdf_path, output_folder)
            else:
                return "Unsupported file type.", 400

            extracted_text = extract_text_from_images(image_paths)
            result_docx_path = os.path.join(output_folder, "extracted_text.docx")
            doc = Document()
            for line in extracted_text.splitlines():
                doc.add_paragraph(line)
            doc.save(result_docx_path)

            session["result_docx"] = result_docx_path
        except Exception as e:
            print("Error:", e)
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
    """Clear session data and reset the application."""
    reset_session()
    return redirect(url_for("upload"))


def reset_session():
    """Helper function to clear session data and delete temporary files."""
    file_paths = session.pop("uploaded_file_paths", [])
    result_docx = session.pop("result_docx", None)

    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)

    if result_docx and os.path.exists(result_docx):
        shutil.rmtree(os.path.dirname(result_docx), ignore_errors=True)


if __name__ == "__main__":
    app.run(debug=True)
