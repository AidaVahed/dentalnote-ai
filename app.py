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

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)


load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return 'Database initialized!'

@app.route('/patients', methods=['POST'])
def create_patient():
    data = request.get_json()
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
        return jsonify({'message': 'Patient created', 'patient_id': new_patient.id}), 201
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
        return jsonify({'message': 'Patient not found'}), 404
    patient_schema = PatientSchema()
    return jsonify(patient_schema.dump(patient)), 200

@app.route('/patients/<int:id>', methods=['PUT'])
def update_patient(id):
    patient = Patient.query.get(id)
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    data = request.get_json()
    try:
        patient.name = data.get('name', patient.name)
        patient.gender = data.get('gender', patient.gender)
        dob = data.get('dob')
        if dob:
            patient.dob = datetime.strptime(dob, '%Y-%m-%d').date()
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
        return jsonify({'message': 'Patient updated', 'patient': patient_schema.dump(patient)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/patients/<int:id>', methods=['DELETE'])
def delete_patient(id):
    patient = Patient.query.get(id)
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404
    db.session.delete(patient)
    db.session.commit()
    return jsonify({'message': 'Patient deleted'}), 200


@app.route('/generate_observation', methods=['POST'])
def generate_observation():
    data = request.get_json()
    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404

    prompt = (
        f"Du bist ein Zahnarzt. Analysiere die folgende Patienten-Historie und "
        f"erstelle eine strukturierte Beobachtung als JSON mit Feldern:\n"
        f"{{\n"
        f"  'observation': string,\n"
        f"  'affected_teeth': [string],\n"
        f"  'recommendation': string\n"
        f"}}\n\n"
        f"Patienten-Historie:\n{patient.health_history}\n\n"
        f"Antwort nur im JSON-Format."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Zahnarzt-Assistent."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.5
        )
        text = response['choices'][0]['message']['content'].strip()

        consultation = Consultation(
            patient_id=patient.id,
            observation=text,
            date=datetime.utcnow()
        )
        db.session.add(consultation)
        db.session.commit()

        return jsonify({'message': 'Observation generated', 'observation': text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload_pdf_and_generate_observation', methods=['POST'])
def upload_pdf_and_generate_observation():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    patient_id = request.form.get('patient_id')
    if not patient_id:
        return jsonify({'error': 'patient_id is required'}), 400
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()

        prompt = (
            f"Du bist ein Zahnarzt. Hier ist das Transkript eines Patientenberichts:\n"
            f"{text}\n\n"
            f"Erstelle bitte eine gut formulierte Beobachtung in korrektem Deutsch, "
            f"die zahnärztliche Befunde wie z.B. Karies an Zahn A2 oder Implantate erwähnt. "
            f"Formatiere die Antwort als JSON mit Feldern:\n"
            f"{{\n"
            f"  'observation': string,\n"
            f"  'affected_teeth': [string],\n"
            f"  'recommendation': string\n"
            f"}}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,

        )
        observation_text = response.choices[0].message.content.strip()

        consultation = Consultation(
            patient_id=patient.id,
            observation=observation_text,
            date=datetime.utcnow()
        )
        db.session.add(consultation)
        db.session.commit()

        return jsonify({'message': 'Observation generated from PDF', 'observation': observation_text}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=8000, debug=True)
