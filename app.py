import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import db, Patient, PatientSchema, Consultation
from datetime import datetime
import openai
from config import Config
from dotenv import load_dotenv
import fitz
from flask_cors import CORS
import logging
import json


load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
logging.basicConfig(level=logging.DEBUG)


db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Hilfsfunktion für Input-Validierung
def validate_json(required_fields, data):
    if not data:
        return False, "JSON Body fehlt"
    for field in required_fields:
        if field not in data:
            return False, f"Feld '{field}' fehlt im JSON Body"
    return True, ""

@app.route('/')
def index():
    return 'Datenbank initialisiert!'

@app.route('/patients', methods=['POST'])
def create_patient():
    data = request.get_json()
    valid, msg = validate_json(['user_id', 'name', 'gender', 'dob', 'address', 'phone', 'email'], data)
    if not valid:
        return jsonify({'error': msg}), 400
    try:
        new_patient = Patient(
            user_id=data['user_id'],
            name=data['name'],
            gender=data['gender'],
            dob=datetime.strptime(data['dob'], '%Y-%m-%d').date(),
            address=data['address'],
            phone=data['phone'],
            email=data['email'],
            billing_address=data.get('billing_address'),
            health_history=data.get('health_history'),
            allergies=data.get('allergies'),
            medications=data.get('medications'),
            chronic_diseases=data.get('chronic_diseases'),
            financial_support=data.get('financial_support', False)
        )
        db.session.add(new_patient)
        db.session.commit()
        return jsonify({'message': 'Patient erstellt', 'patient_id': new_patient.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/patients', methods=['GET'])
def get_patients():
    patients = Patient.query.all()
    patient_schema = PatientSchema(many=True)
    return jsonify(patient_schema.dump(patients)), 200

@app.route('/patients/<int:id>', methods=['GET'])
def get_patient(id):
    patient = Patient.query.get(id)
    if not patient:
        return jsonify({'message': 'Patient nicht gefunden'}), 404
    patient_schema = PatientSchema()
    return jsonify(patient_schema.dump(patient)), 200

@app.route('/patients/<int:id>', methods=['PUT'])
def update_patient(id):
    patient = Patient.query.get(id)
    if not patient:
        return jsonify({'message': 'Patient nicht gefunden'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Kein JSON Body erhalten'}), 400
    try:
        if 'dob' in data:
            patient.dob = datetime.strptime(data['dob'], '%Y-%m-%d').date()
        patient.name = data.get('name', patient.name)
        patient.gender = data.get('gender', patient.gender)
        patient.address = data.get('address', patient.address)
        patient.phone = data.get('phone', patient.phone)
        patient.email = data.get('email', patient.email)
        patient.billing_address = data.get('billing_address', patient.billing_address)
        patient.health_history = data.get('health_history', patient.health_history)
        patient.allergies = data.get('allergies', patient.allergies)
        patient.medications = data.get('medications', patient.medications)
        patient.chronic_diseases = data.get('chronic_diseases', patient.chronic_diseases)
        patient.financial_support = data.get('financial_support', patient.financial_support)
        db.session.commit()
        patient_schema = PatientSchema()
        return jsonify({'message': 'Patient aktualisiert', 'patient': patient_schema.dump(patient)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/patients/<int:id>', methods=['DELETE'])
def delete_patient(id):
    patient = Patient.query.get(id)
    if not patient:
        return jsonify({'message': 'Patient nicht gefunden'}), 404
    db.session.delete(patient)
    db.session.commit()
    return jsonify({'message': 'Patient gelöscht'}), 200


@app.route('/generate_observation', methods=['POST'])
def generate_observation():
    data = request.get_json()
    valid, msg = validate_json(['patient_id'], data)
    if not valid:
        return jsonify({'error': msg}), 400

    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'message': 'Patient nicht gefunden'}), 404

    if not patient.health_history:
        return jsonify({'error': 'health_history fehlt für diesen Patienten'}), 400

    prompt = (
        f"Du bist ein Zahnarzt. Analysiere die folgende Patienten-Historie und "
        f"erstelle eine strukturierte Beobachtung als JSON mit Feldern:\n"
        f"{{\n"
        f"  \"observation\": string,\n"
        f"  \"affected_teeth\": [string],\n"
        f"  \"recommendation\": string\n"
        f"}}\n\n"
        f"Patienten-Historie:\n{patient.health_history}\n\n"
        f"Antwort nur im JSON-Format."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Zahnarzt-Assistent."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.5
        )
        text = response.choices[0].message.content.strip()


        try:
            observation_json = json.loads(text)
        except json.JSONDecodeError:
            return jsonify({'error': 'Antwort war kein gültiges JSON', 'raw_response': text}), 500

        consultation = Consultation(
            patient_id=patient.id,
            observation=text,
            date=datetime.utcnow()
        )
        db.session.add(consultation)
        db.session.commit()

        return jsonify({'message': 'Observation generiert', 'observation': observation_json}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/upload_pdf_and_generate_observation', methods=['POST'])
def upload_pdf_and_generate_observation():
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'Keine Datei übermittelt'}), 400
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Nur PDF-Dateien sind erlaubt'}), 400

    patient_id = request.form.get('patient_id')
    if not patient_id:
        return jsonify({'error': 'patient_id wird benötigt'}), 400
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient nicht gefunden'}), 404

    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()

        prompt = (
            f"Du bist ein Zahnarzt. Hier ist das Transkript eines Patientenberichts:\n"
            f"{text}\n\n"
            f"Bitte generiere folgende strukturierte JSON-Antwort:\n"
            f"{{\n"
            f"  \"observation\": \"string\",\n"
            f"  \"affected_teeth\": [\"string\"],\n"
            f"  \"recommendation\": \"string\"\n"
            f"}}\n"
            f"Antwort NUR als JSON zurückgeben, ohne Kommentare."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5
        )

        raw_text = response.choices[0].message.content.strip()

        try:
            observation_data = json.loads(raw_text)
        except json.JSONDecodeError:
            return jsonify({'error': 'Antwort war kein gültiges JSON', 'raw_response': raw_text}), 500

        consultation = Consultation(
            patient_id=patient.id,
            observation=raw_text,
            date=datetime.utcnow()
        )
        db.session.add(consultation)
        db.session.commit()

        return jsonify({
            'message': 'Observation aus PDF generiert',
            'observation': observation_data
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
