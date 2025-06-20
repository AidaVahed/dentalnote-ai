from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from datetime import datetime



db = SQLAlchemy()

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    billing_address = db.Column(db.String(255))
    health_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    medications = db.Column(db.Text)
    chronic_diseases = db.Column(db.Text)
    financial_support = db.Column(db.Boolean, default=False)

    consultations = db.relationship('Consultation', backref='patient', lazy=True)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    observation = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class PatientSchema(SQLAlchemyAutoSchema):
    consultations = fields.Nested('ConsultationSchema', many=True)

    class Meta:
        model = Patient
        load_instance = True

class ConsultationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Consultation
        load_instance = True
