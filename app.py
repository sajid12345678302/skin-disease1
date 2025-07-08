from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
import numpy as np
from PIL import Image
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import pdfkit

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change to a secure key

# Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = os.path.join('static', 'Uploaded_Images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max upload

# Load model
model_path = "model/skin_disease_detector-lite1.h5"
if os.path.exists(model_path):
    model = load_model(model_path)
else:
    model = None
    print(f"[ERROR] Model file not found at: {model_path}")

# Class labels
CLASS_NAMES = [
    "Atopic Dermatitis", "Squamous cell carcinoma", "Benign keratosis",
    "Vascular lesion", "Tinea Ringworm Candidiasis", "Melanoma",
    "Melanocytic nevus", "Dermatofibroma",
    "Psoriasis pictures Lichen Planus and related diseases"
]

# PDF generation configuration
WKHTMLTOPDF_PATH = r'D:\wkhtmltopdf\bin\wkhtmltopdf.exe'
if os.path.exists(WKHTMLTOPDF_PATH):
    pdfkit_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
else:
    pdfkit_config = None
    print(f"[ERROR] wkhtmltopdf not found at: {WKHTMLTOPDF_PATH}")

# Simple in-memory user store
users = {}

# Helpers
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def predict_image(file_path):
    try:
        image = Image.open(file_path).convert("RGB")
        img = image.resize((128, 128))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        if model:
            predictions = model.predict(img_array)
            prediction = CLASS_NAMES[np.argmax(predictions)]
            confidence = float(np.max(predictions)) * 100
            return prediction, confidence
        else:
            return None, "Model not loaded."
    except Exception as e:
        return None, f"Error processing image: {e}"

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return render_template('Home_Page.html', error='Please log in first.')

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return render_template('Home_Page.html', error='No file selected.')

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            prediction, confidence = predict_image(file_path)
            if prediction:
                return render_template('Skin_disease.html', pred_output=prediction,
                                       confidence=confidence, user_image=file_path)
            else:
                return render_template('Home_Page.html', error=confidence)
        else:
            return render_template('Home_Page.html', error='Invalid file type.')

    return render_template('Home_Page.html')

@app.route('/get_report', methods=['POST'])
def get_report():
    patient_name = request.form.get('patient_name')
    age = request.form.get('age')
    gender = request.form.get('gender')
    pred_output = request.form.get('pred_output')
    confidence = request.form.get('confidence')
    user_image = request.form.get('user_image')
    date = datetime.now().strftime('%B %d, %Y')

    abs_image_path = os.path.abspath(user_image).replace('\\', '/')
    image_path_for_pdf = f'file:///{abs_image_path}'

    rendered = render_template('report_template.html',
                               patient_name=patient_name, age=age, gender=gender,
                               pred_output=pred_output, confidence=confidence,
                               image_path=image_path_for_pdf, date=date)

    if pdfkit_config:
        pdf = pdfkit.from_string(rendered, False, configuration=pdfkit_config)
        filename = f"SkinReport_{patient_name}_{date}.pdf"
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
    else:
        return "PDF generation not configured properly", 500

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        if email in users:
            return render_template('signup.html', error='Email already registered.')
        users[email] = {
            'username': request.form['username'],
            'password': generate_password_hash(request.form['password'])
        }
        flash('Signup successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)
