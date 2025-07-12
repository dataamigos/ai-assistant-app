
# Personal AI Assistant with Vertex AI, Firestore, GUI, and Voice Input (Final Version with Fixes)

# Step 1: Install Required Libraries (run in terminal):
# pip install google-cloud-aiplatform streamlit pyttsx3 speechrecognition pyaudio google-cloud-firestore

import os
#import pyttsx3
import streamlit as st
import speech_recognition as sr
from google.cloud import aiplatform, firestore
from vertexai.generative_models import GenerativeModel
from datetime import datetime, date
import schedule
import time
import threading
import re



# === CONFIGURATION === #
PROJECT_ID = "hasini-gcp"
LOCATION = "us-central1"

# === SETUP GOOGLE VERTEX AI === #
def setup_vertex():
    aiplatform.init(project=PROJECT_ID, location=LOCATION)

def send_to_gemini(prompt):
    model = GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text

# === SETUP FIRESTORE === #
firestore_client = firestore.Client()
reminder_collection = firestore_client.collection("reminders_by_date")

# === SPEECH TO TEXT === #
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I didn't catch that."
        except sr.RequestError:
            return "Error with the speech service."

# === TEXT TO SPEECH === #
# def speak(text):
#     engine = pyttsx3.init()
#     engine.say(text)
#     engine.runAndWait()

# === REMINDER SAVING === #
def save_reminder(date_str, text, type="manual"):
    doc_ref = reminder_collection.document(date_str)
    doc = doc_ref.get()
    new_reminder = {
        "text": text,
        "timestamp": datetime.utcnow(),
        "type": type
    }
    if doc.exists:
        doc_ref.update({"reminders": firestore.ArrayUnion([new_reminder])})
    else:
        doc_ref.set({"reminders": [new_reminder]})

# === RETRIEVE REMINDERS === #
# def get_reminders_for_date(date_str):
#     doc_ref = reminder_collection.document(date_str).get()
#     if doc_ref.exists:
#         return doc_ref.to_dict()["reminders"]
#     return []

def get_reminders_for_date(query_dt):
    doc_ref = firestore_client.collection("reminders_by_date").document(query_dt)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("reminders", [])
    else:
        return []

def extract_date_from_input(user_input):
    match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
    return match.group(0) if match else None

def get_all_reminders():
    all_docs = reminder_collection.stream()
    reminders = {}
    for doc in all_docs:
        reminders[doc.id] = doc.to_dict().get("reminders", [])
    return dict(sorted(reminders.items()))

# === DAILY SUMMARY === #
def generate_daily_summary():
    today = date.today().strftime("%Y-%m-%d")
    reminders = get_reminders_for_date(today)
    if reminders:
        summary = f"Here are your tasks for today ({today}):\n"
        for r in reminders:
            summary += f"- {r['text']} ({r['type']})\n"
        return summary.strip()
    return "You have no reminders scheduled for today."

# === STREAMLIT APP === #
setup_vertex()
st.title("🎙️ Smart Reminder Assistant")

# === Manual Entry === #
st.header("📅 Manual Entry")
manual_text = st.text_input("Enter your reminder:")
manual_date = st.date_input("Select a date", value=date.today())
if st.button("Save Reminder Manually"):
    save_reminder(manual_date.strftime("%Y-%m-%d"), manual_text, "manual")
    st.success("Reminder saved!")

# === Voice Entry === #
st.header("🎤 Voice Entry")
voice_date = st.date_input("Select date for voice reminder", value=date.today(), key="voice_date")
if st.button("Record Voice Reminder"):
    voice_input = listen()
    if voice_input:
        save_reminder(voice_date.strftime("%Y-%m-%d"), voice_input, "voice")
        st.success(f"Saved: {voice_input}")

#Test button
if st.button("Test Reminder Fetch"):
    test_date = st.text_input("Enter date to test (YYYY-MM-DD)", value=datetime.today().strftime('%Y-%m-%d'))
    reminders = get_reminders_for_date(test_date)
    st.write("Reminders Found:", reminders)

# === Ask Gemini === #
user_date_input = st.text_input("Ask Gemini (e.g. What are my tasks on 2025-07-13?):")

if st.button("Ask Gemini"):
    query_date = extract_date_from_input(user_date_input)
    if query_date:
        reminders = get_reminders_for_date(query_date)
        if reminders:
            reminder_text = "\n".join([f"- {r['text']} ({r['type']})" for r in reminders])
            prompt = f"For {query_date}, here are your reminders:\n{reminder_text}\nCan you summarize or organize them?"
        else:
            prompt = f"No reminders found for {query_date}."
        response = send_to_gemini(prompt)
        st.success(response)
    else:
        st.error("Could not find a valid date in your query.")


# === Daily Summary Button === #
if st.button("📅 Daily Planner Summary"):
    summary = generate_daily_summary()
    st.info(summary)
    speak(summary)

# === Show All Reminders === #
if st.button("📂 Show All Reminders"):
    all_reminders = get_all_reminders()
    for dt, items in all_reminders.items():
        st.markdown(f"### 📌 {dt}")
        for r in items:
            st.write(f"- {r['text']} ({r['type']})")
