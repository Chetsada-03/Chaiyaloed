import os
import subprocess
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print(f"Created folder: {UPLOAD_FOLDER}")
else:
    print(f"Folder already exists: {UPLOAD_FOLDER}")

NEW_UPLOAD_FOLDER = 'newmodel/newupload'
if not os.path.exists(NEW_UPLOAD_FOLDER):
    os.makedirs(NEW_UPLOAD_FOLDER, exist_ok=True)
    print(f"Created folder: {NEW_UPLOAD_FOLDER}")
else:
    print(f"Folder already exists: {NEW_UPLOAD_FOLDER}")

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['NEW_UPLOAD_FOLDER'] = NEW_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 5000 * 2000
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_old_images():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"❌ Error deleting {file_path}: {e}")

def delete_old_new_images():
    for filename in os.listdir(app.config['NEW_UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['NEW_UPLOAD_FOLDER'], filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"❌ Error deleting {file_path}: {e}")

@app.route('/')
def home():
    return render_template('home.html')
#-----------------------------------------------------------------------------------------------#
# Predict page
@app.route('/database', methods=['GET', 'POST'])
def database():
    if request.method == 'POST':
        dataset_name = request.form.get("dataset")  # รับค่าที่ผู้ใช้เลือกจากฟอร์ม

        # แมปค่าที่เลือกไปยังโฟลเดอร์ใน model
        model_mapping = {
            "Water-KMNO4-None": "KMNO4",
            "Water-Salt-None": "Salt",
            "Water-Sugar-None": "Sugar",
            "Water-Salt-Sugar": "Sugar_Salt",
            "Ethanol-Carbosulfan-None": "Carbosulfan"
        }

        model_folder = model_mapping.get(dataset_name)  # ค้นหาโฟลเดอร์ model ที่ตรงกับ dataset
        if not model_folder:
            flash("❌ ข้อมูลที่เลือกไม่ตรงกับฐานข้อมูล กรุณาตรวจสอบอีกครั้ง!", "error")
            return render_template('error.html')

        # ส่งชื่อโฟลเดอร์ model ไปยังหน้า newimage.html
        return render_template('newimage.html', dataset=dataset_name, model_folder=model_folder)

    return render_template('database.html')

@app.route('/resultdatabase', methods=['POST'])
def train():
    return render_template('newimage.html')

@app.route('/newimage')
def newimage():
    return render_template("newimage.html") 

@app.route('/next', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('❌ No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('❌ No image selected for uploading')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        delete_old_images() 

        light_source = request.form.get("Light_source")
        solvent = request.form.get("Solvent")
        solute1 = request.form.get("Solute-1")
        solute2 = request.form.get("Solute-2")

        current_date = datetime.now().strftime("%Y%m%d")
        concentration_1_ppm = "0"
        concentration_2_ppm = "0"
        image_number = "1"

        original_filename = secure_filename(file.filename)
        image_name = os.path.splitext(original_filename)[0] 

        new_filename = f"{current_date}_{light_source}_{solvent}_{solute1}_{concentration_1_ppm}_{solute2}_{concentration_2_ppm}_{image_number}.jpg"

        save_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(save_path)

        return render_template('display.html', filename=new_filename,
                               light_source=light_source, solvent=solvent,
                               solute1=solute1, solute2=solute2)
    else:
        flash('❌ Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)

@app.route('/predict', methods=['POST'])
def predict():
    light_source = request.form.get("light_source")
    solvent = request.form.get("solvent")
    solute1 = request.form.get("solute1")
    solute2 = request.form.get("solute2")

    script_dir = os.path.join(os.path.dirname(__file__), "model", "Python")

    script_mapping = {
        ("LED", "Water", "Salt", "None"): os.path.join(script_dir, "Prepare_for_predict(Salt).py"),
        ("LED", "Water", "Sugar", "None"): os.path.join(script_dir, "Prepare_for_predict(Sugar).py"),
        ("LED", "Ethanol", "Carbosulfan", "None"): os.path.join(script_dir, "Prepare_for_predict(Carbosulfan).py"),
        ("LED", "Water", "Potassium permanganate", "None"): os.path.join(script_dir, "Prepare_for_predict(KMNO4).py"),
        ("LED", "Water", "Sugar", "Salt"): os.path.join(script_dir, "Prepare_for_predict(Sugar_Salt).py")
    }

    script_path = script_mapping.get((light_source, solvent, solute1, solute2))

    if not script_path:
        flash("❌ ข้อมูลที่เลือกไม่ตรงกับฐานข้อมูล กรุณาตรวจสอบอีกครั้ง!", "error")
        return render_template('error.html')

    try:
        process = subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        output, error = process.communicate()

        if process.returncode == 0:
            result = output.strip()
        else:
            result = f"❌ Error in prediction!<br><pre>{error}</pre>"

    except Exception as e:
        result = f"❌ Exception occurred: {str(e)}"

    return render_template('predict.html', result=result,
                           light_source=light_source, solvent=solvent,
                           solute1=solute1, solute2=solute2)

#-----------------------------------------------------------------------------------------------#
# Add-database page
BASE_DIR = 'newdata'
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
    print(f"Created folder: {BASE_DIR}")
else:
    print(f"Folder already exists: {BASE_DIR}")

MODEL_DIR = 'newmodel/Formalin'  
mape_files = {
    "XGB": os.path.join(MODEL_DIR, "XGB_MAPE.pkl"),
    "SVR": os.path.join(MODEL_DIR, "SVR_MAPE.pkl"),
    "RF": os.path.join(MODEL_DIR, "RF_MAPE.pkl"),
    "MLR": os.path.join(MODEL_DIR, "MLR_MAPE.pkl"),
    "MLP": os.path.join(MODEL_DIR, "MLP_MAPE.pkl")
}

@app.route('/add_database')
def adddata():
    return render_template('add_database.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # ดึงข้อมูลจากฟอร์ม
        database_name = request.form['database_name'].strip()
        solvent = request.form['Solvent'].strip()
        solute1 = request.form.get('Solute_1', '').strip()
        solute2 = request.form.get('Solute_2', '').strip()
        light_source = request.form['Light_Source'].strip()
        current_date = datetime.now().strftime("%Y%m%d")

        if not database_name:
            flash("⚠ Database name is required!", "warning")
            return redirect(url_for("adddata"))

        # สร้างโฟลเดอร์ของฐานข้อมูล
        db_folder = os.path.join(BASE_DIR, database_name)
        os.makedirs(db_folder, exist_ok=True)

        uploaded_files = []  

        for i in range(1, 11):
            concentration = request.form.get(f"concentration_{i}", "").strip()
            solute1_name = "Blank" if concentration == "0" else solute1 
            files = request.files.getlist(f"files_{i}")

            for index, file in enumerate(files, start=1):
                if file and allowed_file(file.filename):
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{current_date}_{light_source}_{solvent}_{solute1_name}_{concentration}_{solute2}_0_{index}.{file_extension}"
                    file_path = os.path.join(db_folder, filename)
                    file.save(file_path)
                    uploaded_files.append(filename)

        if not uploaded_files:
            flash("⚠ No files were uploaded!", "warning")
        else:
            flash(f"✅ {len(uploaded_files)} files uploaded successfully!", "success")

        return redirect(url_for("newdatabase"))

    except Exception as e:
        flash(f"❌ Error: {str(e)}", "error")
        return redirect(url_for("adddata"))

@app.route('/newdatabase', methods=['GET'])
def newdatabase():
    try:
        databases = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]

        if not databases:
            flash("⚠ No databases found. Please add a database first.", "warning")

        return render_template("newdatabase.html", databases=databases)

    except Exception as e:
        flash(f"❌ Error loading databases: {str(e)}", "error")
        return render_template("newdatabase.html", databases=[])
    
@app.route('/database_selected', methods=['POST'])
def train_newdata():
    database = request.form.get('database')
    if not database:
        flash("⚠ No database selected!", "warning")
        return redirect(url_for("newdatabase"))

    script_path = os.path.join(BASE_DIR, "Prepare_for_train(Formalin).py")

    if not os.path.exists(script_path):
        flash(f"❌ Script not found: {script_path}", "error")
        return redirect(url_for("newdatabase"))

    try:
        process = subprocess.Popen(
            ["python", script_path, database],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output, error = process.communicate()

        if process.returncode == 0:
            flash(f"✅ Training started for database: {database}", "success")
            result = output.strip()
        else:
            flash(f"❌ Training failed! Error: {error}", "error")
            result = f"❌ Error in training:<br><pre>{error}</pre>"

    except Exception as e:
        flash(f"❌ Exception occurred: {str(e)}", "error")
        result = f"❌ Exception: {str(e)}"

    return render_template("newtraining.html", result=result)

@app.route('/upnewimage')
def upnewimage():
    return render_template("upnewimage.html") 

import subprocess

@app.route('/newupload', methods=['POST'])
def new_upload_image():
    if 'file' not in request.files:
        flash('❌ No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('❌ No image selected for uploading')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        delete_old_new_images()  

        light_source = request.form.get("Light_source")
        solvent = request.form.get("Solvent")
        solute1 = request.form.get("Solute-1")
        solute2 = request.form.get("Solute-2")

        current_date = datetime.now().strftime("%Y%m%d")
        concentration_1_ppm = "0"
        concentration_2_ppm = "0"
        image_number = "1"

        new_filename = f"{current_date}_{light_source}_{solvent}_{solute1}_{concentration_1_ppm}_{solute2}_{concentration_2_ppm}_{image_number}.jpg"

        save_path = os.path.join(app.config['NEW_UPLOAD_FOLDER'], new_filename)
        file.save(save_path)

        script_path = os.path.join(os.path.dirname(__file__), "model", "Python", "Prepare_for_predict(Formalin).py")

        try:
            process = subprocess.Popen(
                ["python", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output, error = process.communicate()

            if process.returncode == 0:
                result = output.strip()
            else:
                result = f"❌ Error in prediction!<br><pre>{error}</pre>"

        except Exception as e:
            result = f"❌ Exception occurred: {str(e)}"

        # **ส่งค่าผลลัพธ์ไปที่ newpredict.html**
        return render_template('newpredict.html', filename=new_filename,
                               light_source=light_source, solvent=solvent,
                               solute1=solute1, solute2=solute2,
                               result=result)
    else:
        flash('❌ Allowed image types are - png, jpg, jpeg, gif')
        return redirect(request.url)



if __name__ == "__main__":
    app.run(debug=True)
