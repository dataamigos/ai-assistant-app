# Updated app.py without voice and pyttsx3 modules for Streamlit Community Cloud deployment

import os
import streamlit as st
from google.cloud import aiplatform, firestore
from vertexai.generative_models import GenerativeModel
from datetime import datetime, date
import pandas as pd

# === CONFIGURATION === #
PROJECT_ID = "hasini-gcp"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash"

def setup_vertex():
    aiplatform.init(project=PROJECT_ID, location=LOCATION)

# === Vertex AI Gemini Function === #
def send_to_gemini(prompt):
    model = GenerativeModel(MODEL_NAME)
    responses = model.generate_content(prompt)
    return responses.text

# === Firestore Setup === #
firestore_client = firestore.Client()
task_collection = firestore_client.collection("tasks")

def add_task(description, due_date):
    task = {
        "description": description,
        "due": due_date.strftime('%Y-%m-%d'),
        "created": datetime.now()
    }
    task_collection.add(task)

def get_tasks():
    tasks = task_collection.stream()
    return [{"description": t.to_dict()["description"], "due": t.to_dict()["due"]} for t in tasks]

def daily_summary():
    today = datetime.now().strftime('%Y-%m-%d')
    tasks_today = [t for t in get_tasks() if t["due"] == today]
    if tasks_today:
        return "Today you have the following tasks:\n" + "\n".join(["- " + t["description"] for t in tasks_today])
    else:
        return "You have no tasks scheduled for today."

def get_reminders_for_date(query_dt):
    query_str = query_dt.strftime('%Y-%m-%d')
    tasks = get_tasks()
    return [t for t in tasks if t['due'] == query_str]

# === Streamlit GUI === #
setup_vertex()
st.title("🧠 Personal AI Assistant")
st.write("Manage tasks, see calendar summaries, and talk to Gemini AI!")

# === Input === #
user_input = st.text_input("What do you want to ask Gemini?")
if st.button("Ask Gemini") and user_input:
    with st.spinner("Thinking..."):
        response = send_to_gemini(user_input)
        st.success(response)

# === Show Tasks === #
if st.button("📋 Show My Tasks"):
    user_tasks = get_tasks()
    if user_tasks:
        df = pd.DataFrame(user_tasks)
        df["due"] = pd.to_datetime(df["due"])
        df = df.sort_values(by="due")
        st.dataframe(df)
    else:
        st.info("No tasks yet!")

# === Add Task Manually === #
with st.expander("➕ Add Task Manually"):
    task_text = st.text_input("Task Description")
    due_date = st.date_input("Due Date", date.today())
    if st.button("Add Task") and task_text:
        add_task(task_text, due_date)
        st.success("Task added!")

# === Daily Summary === #
if st.button("📅 Daily Planner Summary"):
    summary = daily_summary()
    st.info(summary)

# === Filter Tasks by Date === #
with st.expander("🔍 View Tasks for a Specific Date"):
    query_date = st.date_input("Select Date to View Tasks", date.today())
    if st.button("Get Reminders"):
        results = get_reminders_for_date(query_date)
        if results:
            st.write("Reminders:")
            for r in results:
                st.write(f"🔔 {r['description']} (Due: {r['due']})")
        else:
            st.warning("No reminders for this date.")
