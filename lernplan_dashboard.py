st.subheader("Klausurvorbereitung")
with st.form("exam_setup"):
    exam_name = st.text_input("Name der Klausur", value=data["exam"].get("name", ""))
    exam_date = st.date_input("Klausurdatum", value=datetime.date.today() if not data["exam"]["date"] else datetime.datetime.strptime(data["exam"]["date"], "%Y-%m-%d").date())
    chapters_count = st.number_input("Anzahl Kapitel", min_value=1, step=1, value=len(data["exam"]["chapters"]) if data["exam"]["chapters"] else 1)
    setup_submitted = st.form_submit_button("Speichern")
    if setup_submitted:
        data["exam"]["name"] = exam_name
        data["exam"]["date"] = str(exam_date)
        if not data["exam"]["chapters"] or len(data["exam"]["chapters"]) != chapters_count:
            data["exam"]["chapters"] = [{"name": f"Kapitel {i+1}", "steps": [False]*6} for i in range(chapters_count)]
        save_data_to_github(data)
        st.success("Klausurinformationen gespeichert!")

if data["exam"]["date"]:
    st.write(f"📚 **{data['exam'].get('name', 'Klausur')}** – Datum: {data['exam']['date']}")
    days_left = (datetime.datetime.strptime(data["exam"]["date"], "%Y-%m-%d").date() - datetime.date.today()).days
    st.write(f"📅 Noch {days_left} Tage bis zur Klausur")

    total_steps = len(data["exam"]["chapters"]) * 6
    completed_steps = sum(sum(1 for step in chap["steps"] if step) for chap in data["exam"]["chapters"])
    progress = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
    steps_left = total_steps - completed_steps
    daily_target = steps_left / days_left if days_left > 0 else steps_left

    # Donut + Balken nebeneinander
    col_donut, col_bar = st.columns([2, 1])
    with col_donut:
        fig_exam = px.pie(
            names=["Erledigt", "Offen"],
            values=[completed_steps, steps_left],
            hole=0.5,
            title=f"Klausurfortschritt ({progress:.0f}%)",
            color_discrete_sequence=["#00cc96", "#ef553b"]
        )
        st.plotly_chart(fig_exam, use_container_width=True)
    with col_bar:
        st.progress(progress / 100)
        st.write(f"✅ {completed_steps}/{total_steps} Schritte erledigt")

    # Soll/Ist Analyse
    st.info(f"📈 Du musst **{daily_target:.1f} Schritte pro Tag** erledigen, um rechtzeitig fertig zu sein.")

    # Kapitel-Checkboxen
    step_labels = ["Lesen", "Fragen", "25%", "50%", "75%", "100%"]
    for idx, chap in enumerate(data["exam"]["chapters"]):
        st.write(f"**{chap['name']}**")
        cols = st.columns(6)
        for i in range(6):
            with cols[i]:
                data["exam"]["chapters"][idx]["steps"][i] = st.checkbox(step_labels[i], value=chap["steps"][i], key=f"chap_{idx}_step_{i}")
