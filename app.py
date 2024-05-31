import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from docx2pdf import convert
import tempfile
import pythoncom
from ultralytics import YOLO
import shutil

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'static/uploads/'
OUTPUT_FOLDER = 'static/images/'
PREDICTED_FOLDER = 'static/predicted/'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['PREDICTED_FOLDER'] = PREDICTED_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_pdf_to_images(filename, pdf_path, output_folder):
    images = convert_from_path(pdf_path)
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_folder, f'{filename}_page_{i + 1}.png')
        image.save(image_path, 'PNG')
        image_paths.append(image_path)
    return image_paths

def convert_docx_to_pdf(docx_path):
    pythoncom.CoInitialize()
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        temp_pdf.close()
        convert(docx_path, temp_pdf.name)
        pdf_path = temp_pdf.name
    pythoncom.CoUninitialize()
    return pdf_path

@app.route('/')
def index():
    return render_template('index.html')

def predict_and_segment(image_paths):
    model_path = 'static/yolov8_model/best.pt'
    model = YOLO(model_path)

    original_and_segmented_paths = []

    for image_path in image_paths:
        # Perform prediction
        results = model.predict(source=image_path, conf=0.5, save=True)

        # Extract the directory and original filename
        image_dir = os.path.dirname(image_path)
        image_filename = os.path.basename(image_path)
        image_name, image_ext = os.path.splitext(image_filename)

        # Define the new filename
        predicted_filename = f"{image_name}_predicted{image_ext}"
        predicted_image_path = os.path.join(app.config['PREDICTED_FOLDER'], predicted_filename)

        # Move the saved image from the default 'runs' directory to the desired location
        runs_dir = 'runs/segment'   # The default runs directory for YOLOv8
        last_run_dir = sorted(os.listdir(runs_dir))[-1]  # Get the latest run directory
        latest_run_path = os.path.join(runs_dir, last_run_dir)

        # The image is usually saved with the same name as the source image in the latest run directory
        source_saved_image_path = os.path.join(latest_run_path, image_filename)

        # Ensure the source saved image path exists and move it to the new location
        if os.path.exists(source_saved_image_path):
            shutil.move(source_saved_image_path, predicted_image_path)
            original_and_segmented_paths.append((image_path, predicted_image_path))
        else:
            print("Error: Predicted image was not found in the expected location.")

    return original_and_segmented_paths

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if filename.rsplit('.', 1)[1].lower() == 'pdf':
            image_paths = convert_pdf_to_images(filename, file_path, app.config['OUTPUT_FOLDER'])
        else:
            # Convert DOCX to PDF first
            pdf_path = convert_docx_to_pdf(file_path)
            # Then convert the PDF to images
            image_paths = convert_pdf_to_images(filename, pdf_path, app.config['OUTPUT_FOLDER'])
            # Cleanup the temporary PDF file
            os.remove(pdf_path)

        # Run your YOLOv8 model here and generate segmented images
        original_and_segmented_paths = predict_and_segment(image_paths)

        response_paths = [{'original': os.path.relpath(orig, start='static'), 'segmented': os.path.relpath(seg, start='static')}
                          for orig, seg in original_and_segmented_paths]

        return jsonify({'image_paths': response_paths}), 200

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['OUTPUT_FOLDER']):
        os.makedirs(app.config['OUTPUT_FOLDER'])
    if not os.path.exists(app.config['PREDICTED_FOLDER']):
        os.makedirs(app.config['PREDICTED_FOLDER'])
    app.run(debug=True)