import streamlit as st
import json
import os
import datetime
import smtplib
from email.mime.text import MIMEText
import requests
import plotly.express as px

# Datei für Persistenz (Cloud-ready)
DATA_FILE = "lernplan_allin.json"

# Daten laden oder initialisieren
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        return {
            "tasks": [],
            "points": 0,
            "habits": {},
            "badges": [],
            "last_update": str(datetime.date.today())
        }

# Daten speichern
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Punkte pro Stunde
POINTS_PER_HOUR = 10

# Daten laden
data = load_data()

# Reset für neuen Tag
if data["last_update"] != str(datetime.date.today()):
    for habit in data["habits"]:
        if data["habits"][habit]["done"]:
            data["habits"][habit]["streak"] += 1
        else:
            data["habits"][habit]["streak"] = 0
        data["habits"][habit]["done"] = False
    data["last_update"] = str(datetime.date.today())
    save_data(data)

st.title("📚 Lernplan Dashboard – All-in-One")
st.write("Aufgaben, Habits, Belohnungen, Badges, Push & Mail – mobil und cloud-ready!")

# Kreisdiagramm für Fortschritt
if data["tasks"]:
    total_duration = sum(task["duration"] for task in data["tasks"])
    completed_duration = sum(task["duration"] for task in data["tasks"] if task["done"])
else:
    total_duration = 0
    completed_duration = 0

fig = px.pie(
    names=["Erledigt", "Offen"],
    values=[completed_duration, max(total_duration - completed_duration, 0)],
    title="Tagesfortschritt",
    color_discrete_sequence=["green", "red"]
)
st.plotly_chart(fig)

st.write(f"✅ Erledigt: {completed_duration}h / 🎯 Ziel: {total_duration}h")

# Punkte und Level
st.subheader("Score & Level")
st.write(f"Punkte: {data['points']}")
level = data['points'] // 100
st.write(f"Level: {level}")

# Badges für Streaks
for habit in data["habits"]:
    if data["habits"][habit]["streak"] >= 7 and f"{habit}-Meister" not in data["badges"]:
        data["badges"].append(f"{habit}-Meister")
        save_data(data)

st.write("Badges: " + ", ".join(data["badges"]) if data["badges"] else "Noch keine Badges")

# Habit-Manager
st.subheader("Habit-Tracker & Manager")
for habit in list(data["habits"].keys()):
    col1, col2, col3 = st.columns([3, 1, 1])
    if col1.checkbox(habit, value=data["habits"][habit]["done"], key=f"habit_{habit}"):
        data["habits"][habit]["done"] = True
        save_data(data)
    col2.write(f"Streak: {data['habits'][habit]['streak']} Tage")
    if col3.button("Löschen", key=f"delete_{habit}"):
        del data["habits"][habit]
        save_data(data)
        st.experimental_rerun()

# Neues Habit hinzufügen
with st.form("add_habit"):
    new_habit = st.text_input("Neues Habit hinzufügen")
    submitted_habit = st.form_submit_button("Hinzufügen")
    if submitted_habit and new_habit:
        data["habits"][new_habit] = {"done": False, "streak": 0}
        save_data(data)
        st.success("Habit hinzugefügt!")

# Aufgaben anzeigen
st.subheader("Deine Aufgaben")
for i, task in enumerate(data["tasks"]):
    col1, col2 = st.columns([3, 1])
    col1.write(f"{task['title']} – {task['duration']}h – Deadline: {task['deadline']}")
    if col2.checkbox("Erledigt", value=task["done"], key=f"done_{i}"):
        if not task["done"]:
            task["done"] = True
            data["points"] += task["duration"] * POINTS_PER_HOUR
            save_data(data)
    else:
        task["done"] = False
        save_data(data)

# Neue Aufgabe hinzufügen
st.subheader("Neue Aufgabe hinzufügen")
with st.form("add_task"):
    title = st.text_input("Titel der Aufgabe")
    duration = st.number_input("Dauer (in Stunden)", min_value=0.5, step=0.5)
    deadline = st.date_input("Deadline")
    submitted = st.form_submit_button("Hinzufügen")
    if submitted and title:
        data["tasks"].append({"title": title, "duration": duration, "done": False, "deadline": str(deadline)})
        save_data(data)
        st.success("Aufgabe hinzugefügt!")

# E-Mail-Benachrichtigung (SMTP)
st.subheader("E-Mail-Benachrichtigung")
email = st.text_input("Deine E-Mail-Adresse")
if st.button("Sende Test-Mail") and email:
    try:
        msg = MIMEText("Dies ist deine Lern-Reminder-Nachricht: Check-In nicht vergessen!")
        msg["Subject"] = "Lernplan Erinnerung"
        msg["From"] = "dein.email@example.com"
        msg["To"] = email
        st.success("Test-Mail vorbereitet (SMTP-Konfiguration erforderlich).")
    except Exception as e:
        st.error(f"Fehler: {e}")

# Push-Benachrichtigung via Pushover
st.subheader("Push-Benachrichtigung (Pushover)")
pushover_token = st.text_input("Pushover API Token")
pushover_user = st.text_input("Pushover User Key")
if st.button("Sende Test-Push") and pushover_token and pushover_user:
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data={
            "token": pushover_token,
            "user": pushover_user,
            "message": "Dies ist deine Lern-Reminder-Push-Nachricht!"
        })
        if response.status_code == 200:
            st.success("Push-Nachricht gesendet!")
        else:
            st.error(f"Fehler: {response.text}")
    except Exception as e:
        st.error(f"Fehler: {e}")

# Automatische Erinnerungen Hinweis
st.subheader("Automatische tägliche Erinnerungen")
st.write("Für Cloud: Nutze Streamlit Cloud oder Cron-Jobs für Check-In (08:00) und Tagesziel (20:00).")
st.code("""
# Beispiel für Cron:
0 8 * * * curl -X GET https://dein-streamlit-cloud-link   # Morgens Check-In
0 20 * * * curl -X GET https://dein-streamlit-cloud-link  # Abends Tagesziel
""", language="bash")

st.info("Für Cloud-Deployment: Lade dieses Projekt auf Streamlit Cloud hoch (https://share.streamlit.io).")