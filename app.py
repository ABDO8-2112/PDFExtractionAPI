
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
from extractor import extract_structured_content
from helpers import save_json_to_mysql

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
IMAGE_FOLDER = 'images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER

@app.route('/images/<pdf_name>/<filename>')
def serve_image(pdf_name, filename):
    return send_from_directory(os.path.join(IMAGE_FOLDER, pdf_name), filename)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'files' not in request.files:
        return jsonify({"error": "'files' field is missing"}), 400

    files = request.files.getlist('files')
    results = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract only vector graphics (diagrams, lines, shapes)
        image_urls = extract_structured_content(pdf_path = file_path, output_base_dir=app.config['IMAGE_FOLDER'])

        save_json_to_mysql(
        data=image_urls,
        host="localhost",
        user="sa",
        password="ABCDEFGH",
        database="pdfextractdatabase"
    )
        # Return a JSON structure containing the image URLs
        json_result = {
            "response": {
                "book": None,
                "subject": None,
                "chapters": [
                    {
                        "chapterName": "Sample Chapter",
                        "topics": [],
                        "exercises": []
                    }
                ]
            },
            "uploaded_files": image_urls
        }
        results.append(json_result)

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
