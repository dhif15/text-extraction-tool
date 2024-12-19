import os
import shutil
import tempfile
from flask import Flask, request, render_template, send_file, redirect, url_for, session, jsonify
from pdf2image import convert_from_path
from pytesseract import image_to_string
from docx import Document
import win32com.client
import locale

# Flask App Initialization
app = Flask(__name__)
app.secret_key = "secret_key"

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


def simplify_path(path):
    return os.path.normpath(path)


def convert_word_to_pdf(input_word_path, output_pdf_path):
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(simplify_path(input_word_path))
        doc.SaveAs(simplify_path(output_pdf_path), FileFormat=17)
        doc.Close()
    finally:
        word.Quit()


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
        uploaded_file = request.files.get("file")
        if not uploaded_file:
            return jsonify({"error": "No file uploaded"}), 400
        try:
            temp_folder = tempfile.mkdtemp()
            file_path = os.path.join(temp_folder, uploaded_file.filename)
            uploaded_file.save(file_path)
            session["uploaded_file_path"] = file_path
            return jsonify({"redirect": url_for("process")}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template("index.html")


@app.route("/process", methods=["GET"])
def process():
    file_path = session.get("uploaded_file_path")
    if not file_path or not os.path.exists(file_path):
        return "File not found", 404

    result_docx_path = session.get("result_docx")
    if not result_docx_path:
        try:
            output_folder = tempfile.mkdtemp()
            if file_path.endswith(".pdf"):
                # Process all pages of the PDF
                image_paths = convert_pdf_to_images(file_path, output_folder)
            else:
                pdf_path = os.path.join(output_folder, "temp.pdf")
                convert_word_to_pdf(file_path, pdf_path)
                image_paths = convert_pdf_to_images(pdf_path, output_folder)

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
    file_path = session.pop("uploaded_file_path", None)
    result_docx = session.pop("result_docx", None)

    if file_path and os.path.exists(file_path):
        shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)

    if result_docx and os.path.exists(result_docx):
        shutil.rmtree(os.path.dirname(result_docx), ignore_errors=True)

    return redirect(url_for("upload"))


if __name__ == "__main__":
    app.run(debug=True)
