import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, auth
import uuid
from fpdf import FPDF
import base64
import os

# -------------------- Firebase Init --------------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred, {
        'databaseURL': f"https://{firebase_config['project_id']}.firebaseio.com"
    })

# -------------------- Utility --------------------
def save_result_as_pdf(student_name, standard, subject, score, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Exam Result", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Name: {student_name}", ln=True)
    pdf.cell(200, 10, txt=f"Standard: {standard}", ln=True)
    pdf.cell(200, 10, txt=f"Subject: {subject}", ln=True)
    pdf.cell(200, 10, txt=f"Score: {score}/{total}", ln=True)

    file_path = f"{uuid.uuid4()}_result.pdf"
    pdf.output(file_path)

    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    os.remove(file_path)

    href = f'<a href="data:application/octet-stream;base64,{b64}" download="result.pdf">📥 Download Result</a>'
    return href

# -------------------- Admin Panel --------------------
def admin_panel():
    st.subheader("🛠️ Admin Panel - Add Users")

    name = st.text_input("Full Name")
    contact = st.text_input("Contact Number")
    role = st.selectbox("Role", ["Student", "Teacher"])
    parent_name = st.text_input("Parent Name") if role == "Student" else None
    standard = st.selectbox("Standard", ["1","2","3","4","5","6","7"]) if role == "Student" else None

    if st.button("Add User"):
        username = parent_name.replace(" ", "").lower() if role == "Student" else name.replace(" ", "").lower()
        password = contact  # Default password = contact number
        
        # Store in Firebase
        user_id = str(uuid.uuid4())
        db.reference("users").child(user_id).set({
            "name": name,
            "username": username,
            "password": password,
            "contact": contact,
            "role": role,
            "parent_name": parent_name if role == "Student" else "",
            "standard": standard if role == "Student" else ""
        })
        st.success(f"✅ {role} added successfully! Username: {username}, Password: {password}")

# -------------------- Login --------------------
def login_user():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # 1️⃣ Admin login
        if username == "omkar" and password == "omkar":
            st.session_state.user = {"role": "Admin", "name": "Admin Omkar"}
            st.success("Welcome Admin Omkar")
            return
        
        # 2️⃣ Student/Teacher login
        users = db.reference("users").get()
        for uid, user_data in users.items():
            if user_data.get("username") == username and user_data.get("password") == password:
                st.session_state.user = {**user_data, "uid": uid}
                st.success(f"Welcome {user_data['name']} ({user_data['role']})")
                return
        st.error("Invalid credentials")

# -------------------- Teacher Panel --------------------
def teacher_panel():
    st.subheader("📚 Teacher - Add Question Paper")
    standard = st.selectbox("Select Standard", ["1","2","3","4","5","6","7"])
    subject = st.selectbox("Subject", ["Maths", "Marathi", "English", "GK"])
    question = st.text_area("Question")
    options = [st.text_input(f"Option {i+1}") for i in range(4)]
    correct_ans = st.selectbox("Correct Answer", ["1","2","3","4"])

    if st.button("Add Question"):
        q_id = str(uuid.uuid4())
        db.reference(f"questions/{standard}/{subject}").child(q_id).set({
            "question": question,
            "options": options,
            "answer": correct_ans
        })
        st.success("✅ Question added successfully!")

# -------------------- Student Panel --------------------
def student_panel():
    st.subheader("📝 Attempt Question Paper")
    standard = st.session_state.user["standard"]
    subject = st.selectbox("Subject", ["Maths", "Marathi", "English", "GK"])

    questions = db.reference(f"questions/{standard}/{subject}").get() or {}
    answers = {}

    for qid, qdata in questions.items():
        st.write(f"**Q: {qdata['question']}**")
        ans = st.radio("Select answer", qdata["options"], key=qid)
        answers[qid] = ans

    if st.button("Submit"):
        score = 0
        for qid, qdata in questions.items():
            if answers[qid] == qdata["options"][int(qdata["answer"]) - 1]:
                score += 1

        st.success(f"Your score: {score}/{len(questions)}")
        st.markdown(save_result_as_pdf(
            student_name=st.session_state.user["name"],
            standard=standard,
            subject=subject,
            score=score,
            total=len(questions)
        ), unsafe_allow_html=True)

# -------------------- Main --------------------
st.title("Student–Teacher Exam Portal")

if "user" not in st.session_state:
    login_user()
else:
    role = st.session_state.user["role"]
    if role == "Admin":
        admin_panel()
    elif role == "Teacher":
        teacher_panel()
    else:
        student_panel()
