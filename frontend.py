import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("Patientenverwaltung")

if st.button("Patientenliste laden"):
    response = requests.get(f"{API_URL}/patients")
    if response.status_code == 200:
        patients = response.json()
        for p in patients:
            st.write(f"ID: {p['id']}, Name: {p['name']}, E-Mail: {p['email']}")
    else:
        st.error("Fehler beim Laden der Patienten.")

st.header("Neuen Patienten anlegen")
with st.form("create_patient"):
    name = st.text_input("Name")
    gender = st.selectbox("Geschlecht", ["männlich", "weiblich", "divers"])
    dob = st.date_input("Geburtsdatum")
    address = st.text_input("Adresse")
    phone = st.text_input("Telefon")
    email = st.text_input("E-Mail")
    billing_address = st.text_input("Rechnungsadresse (optional)")
    health_history = st.text_area("Krankengeschichte (optional)")
    allergies = st.text_input("Allergien (optional)")
    medications = st.text_input("Medikamente (optional)")
    chronic_diseases = st.text_input("Chronische Erkrankungen (optional)")
    financial_support = st.checkbox("Finanzielle Unterstützung")
    user_id = st.number_input("User-ID", min_value=1, step=1)
    submitted = st.form_submit_button("Anlegen")
    if submitted:
        data = {
            "user_id": user_id,
            "name": name,
            "gender": gender,
            "dob": dob.strftime("%Y-%m-%d"),
            "address": address,
            "phone": phone,
            "email": email,
            "billing_address": billing_address,
            "health_history": health_history,
            "allergies": allergies,
            "medications": medications,
            "chronic_diseases": chronic_diseases,
            "financial_support": financial_support
        }

        resp = requests.post(f"{API_URL}/patients", json=data)
        if resp.status_code == 201:
            st.success("Patient erfolgreich angelegt!")
        else:
            try:
                error_json = resp.json()
                st.error(f"Fehler: {error_json}")
            except Exception:
                st.error(f"Fehler: {resp.text}")

st.header("Patientendaten anzeigen/bearbeiten")
patient_id = st.number_input("Patienten-ID", min_value=1, step=1)
if st.button("Patient laden"):
    resp = requests.get(f"{API_URL}/patients/{patient_id}")
    if resp.status_code == 200:
        patient = resp.json()
        st.json(patient)
    else:
        st.error("Patient nicht gefunden.")


st.header("Observation aus PDF-Transkript generieren")

patient_id_for_pdf = st.number_input("Patienten-ID für Observation", min_value=1, step=1, key="pdf_patient_id")

uploaded_file = st.file_uploader("Lade ein PDF-Transkript hoch", type=["pdf"], key="pdf_upload")

if uploaded_file is not None:
    if st.button("PDF hochladen und Observation generieren"):
        files = {
            "pdf_file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")
        }
        data = {"patient_id": patient_id_for_pdf}
        response = requests.post(f"{API_URL}/upload_pdf_and_generate_observation", data=data, files=files)

        if response.status_code == 200:
            observation = response.json().get("observation")
            st.success("Observation generiert:")
            st.json(observation)
        else:
            st.error(f"Fehler: {response.text}")
