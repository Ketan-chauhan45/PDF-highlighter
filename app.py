# app.py
from flask import Flask, request, send_from_directory, render_template_string
import os
from project import Project

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML template for the upload form
HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>PDF Highlighter</title>
</head>
<body>
    <h1>Upload PDF and Enter Query</h1>
    <form method="post" enctype="multipart/form-data">
        <label for="query">Query:</label>
        <input type="text" id="query" name="query" required><br><br>
        <label for="pdf_file">PDF File:</label>
        <input type="file" id="pdf_file" name="pdf_file" accept=".pdf" required><br><br>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_query = request.form.get('query')
        pdf_file = request.files.get('pdf_file')
        if not pdf_file or not input_query:
            return "Missing file or query."
        
        # Save the uploaded PDF
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
        pdf_file.save(pdf_path)
        
        # Define the output filename/path
        output_pdf_filename = 'highlighted_' + pdf_file.filename
        output_pdf_path = os.path.join(UPLOAD_FOLDER, output_pdf_filename)
        
        # Run the PDF processing using your Project class
        model = "sentence-transformers/all-MiniLM-L6-v2"
        threshold = 0.8
        project_instance = Project(
            pdf_path=pdf_path,
            model_path=model,
            query=input_query,
            threshold=threshold,
            output_pdf_path=output_pdf_path
        )
        result = project_instance.run()
        if result.startswith("Highlighted PDF saved"):
            # Return an HTML page that embeds the highlighted PDF and offers a download link
            html_result = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Highlighted PDF</title>
            </head>
            <body>
                <h1>Your Highlighted PDF</h1>
                <iframe src="/view/{output_pdf_filename}" width="100%" height="800px"></iframe>
                <p><a href="/download/{output_pdf_filename}">Download PDF</a></p>
            </body>
            </html>
            """
            return html_result
        else:
            return result
    return render_template_string(HTML_FORM)

# Route to download the PDF file
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# Route to view the PDF inline
@app.route('/view/<filename>')
def view(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)

if __name__ == '__main__':
    app.run()
