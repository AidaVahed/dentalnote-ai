from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import db, Patient, PatientSchema, Consultation
from datetime import datetime
import os
import openai
from config import Config
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

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
            dob=datetime.strptime(data['dob'], '%Y-%m-%d'),
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
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/patients', methods=['GET'])
def get_patients():
    patients = Patient.query.all()
    result = []

    for patient in patients:
        result.append({
            'id': patient.id,
            'name': patient.name,
            'email': patient.email,
            'phone': patient.phone,
            'address': patient.address,
            'dob': patient.dob.strftime('%Y-%m-%d') if patient.dob else None,
            'gender': patient.gender,
            'allergies': patient.allergies,
            'medications': patient.medications,
            'chronic_diseases': patient.chronic_diseases,
            'billing_address': patient.billing_address,
            'financial_support': patient.financial_support
        })

    return jsonify(result), 200

@app.route('/patients/<int:id>', methods=['GET'])
def get_patient(id):
    patient = Patient.query.get(id)
    if patient:
        return jsonify({
            'id': patient.id,
            'name': patient.name,
            'gender': patient.gender,
            'dob': patient.dob,
            'address': patient.address,
            'phone': patient.phone,
            'email': patient.email,
            'billing_address': patient.billing_address,
            'health_history': patient.health_history,
            'allergies': patient.allergies,
            'medications': patient.medications,
            'chronic_diseases': patient.chronic_diseases,
            'financial_support': patient.financial_support
        })
    else:
        return jsonify({'message': 'Patient not found'}), 404

patient_schema = PatientSchema()

@app.route('/patients/<int:id>', methods=['PUT'])
def update_patient(id):
    patient = Patient.query.get(id)

    if not patient:
        return jsonify({'message': 'Patient not found'}), 404

    data = request.get_json()

    patient.name = data.get('name', patient.name)
    patient.gender = data.get('gender', patient.gender)

    dob = data.get('dob')
    if dob:
        try:
            patient.dob = datetime.strptime(dob, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

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

    return jsonify({'message': 'Patient updated successfully', 'patient': patient_schema.dump(patient)}), 200

@app.route('/patients/<int:id>', methods=['DELETE'])
def delete_patient(id):
    patient = db.session.get(Patient, id)
    if not patient:
        return jsonify({'message': 'Patient not found'}), 404

    db.session.delete(patient)
    db.session.commit()

    return jsonify({'message': 'Patient deleted successfully'}), 200


@app.route('/generate_observation', methods=['POST'])
def generate_observation():
    data = request.get_json()

    patient_id = data.get('patient_id')
    patient = Patient.query.get(patient_id)

    if not patient:
        return jsonify({'message': 'Patient not found'}), 404

    observation_prompt = f"Generate an observation for a patient with the following health data: {patient.health_history}"

    openai.api_key = OPENAI_API_KEY

    try:
        response = openai.completions.create(
            model="gpt-3.5-turbo",
            prompt=observation_prompt,
            max_tokens=150
        )
        observation = response['choices'][0]['text'].strip()

        consultation = Consultation(
            patient_id=patient.id,
            observation=observation
        )
        db.session.add(consultation)
        db.session.commit()

        return jsonify({'message': 'Observation generated', 'observation': observation}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
