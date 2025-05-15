from flask import Flask, render_template, request, send_file
from transformers import pipeline
from docx import Document
from langdetect import detect
from fpdf import FPDF
import tempfile
import re

app = Flask(__name__)

# Load the English summarization model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")


def extract_text(file):
    if file.filename.endswith('.txt'):
        return file.read().decode('utf-8')
    elif file.filename.endswith('.docx'):
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

def highlight_keywords(summary, keywords):
    for word in keywords:
        summary = re.sub(fr"\b({re.escape(word)})\b", r"<mark>\1</mark>", summary, flags=re.IGNORECASE)
    return summary

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    highlighted = ""
    original_text = ""
    selected_lang = "English"

    if request.method == 'POST':
        input_text = request.form.get('input_text', "")
        file = request.files.get('file')
        keywords = request.form.get('keywords', "").split(',')
        selected_lang = request.form.get('language', 'English')

        if file and file.filename != "":
            input_text = extract_text(file)

        if input_text.strip():
            original_text = input_text.strip()
            detected_lang = detect(original_text)
            if selected_lang.lower() != "english" and detected_lang != 'en':
                summary = "❌ Currently, only English summarization is supported."
            else:
                try:
                    result = summarizer(original_text, max_length=130, min_length=30, do_sample=False)
                    summary = result[0]['summary_text']
                    highlighted = highlight_keywords(summary, [k.strip() for k in keywords if k.strip()])
                except Exception as e:
                    summary = f"Error during summarization: {str(e)}"
        else:
            summary = "⚠️ Please provide valid input."

    return render_template('index.html', summary=summary, highlighted=highlighted,
                           original_text=original_text, language=selected_lang)

@app.route('/download', methods=['POST'])
def download_summary():
    summary_text = request.form.get('summary_text', '')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, summary_text)
        pdf.output(tmpfile.name)
        return send_file(tmpfile.name, as_attachment=True, download_name="summary.pdf")

if __name__ == '__main__':
    app.run(debug=True)
