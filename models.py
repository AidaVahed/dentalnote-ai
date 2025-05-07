from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from marshmallow import Schema, fields

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patients = db.relationship('Patient', backref='dentist', lazy=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
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
    date = db.Column(db.DateTime, default=datetime.utcnow)
    observation = db.Column(db.Text)
    treatment_plan = db.Column(db.Text)
    follow_up_reminder = db.Column(db.String(255))

class PatientSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    name = fields.Str()
    gender = fields.Str()
    dob = fields.Date()
    address = fields.Str()
    phone = fields.Str()
    email = fields.Str()
    billing_address = fields.Str()
    health_history = fields.Str()
    allergies = fields.Str()
    medications = fields.Str()
    chronic_diseases = fields.Str()
    financial_support = fields.Bool()
