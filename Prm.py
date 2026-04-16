import streamlit as st
import sqlite3
import re
from PyPDF2 import PdfReader

# --- 1. PAGE CONFIG & UI ---
st.set_page_config(page_title=" HR Portal", layout="wide")

bg_url = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1920&q=80"

st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(10, 10, 20, 0.9), rgba(10, 10, 20, 0.9)), url("{bg_url}");
        background-size: cover; background-attachment: fixed; color: #ffffff !important;
    }}
    .centered-container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding-top: 30px; }}
    label, p, h1, h2, h3, h4, span, .stMarkdown, .stMetric {{ color: #ffffff !important; }}
    [data-testid="stSidebar"] {{ background-color: #050505 !important; border-right: 2px solid #00f2ff; }}
    
    .card-short {{ background: rgba(0, 242, 255, 0.1); padding: 15px; border-radius: 10px; border: 1px solid #00f2ff; margin-bottom: 10px; }}
    .card-reject {{ background: rgba(239, 68, 68, 0.1); padding: 15px; border-radius: 10px; border: 1px solid #ef4444; margin-bottom: 10px; }}

    div.stButton > button {{
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%) !important;
        color: white !important; border-radius: 8px; font-weight: 700;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = 'hr_portal_final.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS resumes 
             (id INTEGER PRIMARY KEY, real_name TEXT, category TEXT, score INTEGER, content BLOB)''')
conn.commit()

JOB_ROLES = ["Backend Developer", "Data Scientist", "Full Stack Developer", "AI/ML Engineer", "UI/UX Designer"]

# --- 3. LOGIC ---
def extract_real_name(text):
    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 2]
    if lines:
        clean_name = re.sub(r'[^a-zA-Z\s]', '', lines[0])
        return clean_name.strip().title()
    return "Candidate"

# --- 4. LOGIN ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.markdown('<div class="centered-container"><img src="https://cdn-icons-png.flaticon.com/512/6681/6681204.png" width="80"><h1 style="color: #00f2ff;">HR PORTAL</h1></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 0.8, 1])
    with col2:
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN"):
                if u == "admin" and p == "bca123":
                    st.session_state['auth'] = True
                    st.rerun()

# --- 5. MAIN APP ---
else:
    if 'page' not in st.session_state: st.session_state['page'] = "📊 Dashboard"

    with st.sidebar:
        st.markdown("<h2 style='color: #00f2ff;'>HR MENU</h2>", unsafe_allow_html=True)
        nav_options = ["📊 Dashboard", "📤 Analyze & Results", "✅ Shortlisted", "❌ Rejected", "📄 Job Offer"]
        
        try:
            current_idx = nav_options.index(st.session_state['page'])
        except:
            current_idx = 0
            
        nav = st.radio("GO TO", nav_options, index=current_idx)
        st.session_state['page'] = nav
        
        if st.button("🔒 LOGOUT & CLEAR"):
            c.execute("DELETE FROM resumes")
            conn.commit()
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- DASHBOARD ---
    if st.session_state['page'] == "📊 Dashboard":
        st.title("HR Dashboard")
        s_count = c.execute("SELECT COUNT(*) FROM resumes WHERE score >= 50").fetchone()[0]
        r_count = c.execute("SELECT COUNT(*) FROM resumes WHERE score < 50").fetchone()[0]
        c1, c2 = st.columns(2)
        c1.metric("Total Shortlisted", s_count)
        c2.metric("Total Rejected", r_count)

    # --- ANALYZE & RESULTS ---
    elif st.session_state['page'] == "📤 Analyze & Results":
        st.title("candidate short list")
        role = st.selectbox("Select Job Role for Analysis", JOB_ROLES)
        files = st.file_uploader("Upload Resumes (PDF)", accept_multiple_files=True, type="pdf")
        
        if files:
            # UNIQUE KEY: Combines Role Name + Number of Files
            # This ensures if you change the Role, the AI re-analyzes even if files stay the same
            analysis_id = f"{role}_{len(files)}"
            
            if 'last_id' not in st.session_state or st.session_state['last_id'] != analysis_id:
                with st.spinner(f"Re-analyzing resumes for {role} role..."):
                    for f in files:
                        reader = PdfReader(f)
                        text = "".join([p.extract_text() for p in reader.pages])
                        name = extract_real_name(text)
                        
                        # Logic: Look for the first word of the role (e.g., 'Python') in text
                        keyword = role.split()[0].lower()
                        score = 85 if keyword in text.lower() else 35
                        
                        c.execute("INSERT INTO resumes (real_name, category, score, content) VALUES (?,?,?,?)", 
                                  (name, role, score, f.read()))
                    
                    conn.commit()
                    st.session_state['last_id'] = analysis_id
                    st.toast(f"Analysis Complete for {role}!", icon='✅')
                    st.rerun()
        
        st.write("---")
        st.subheader(f"Current Results for {role}")
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("<h4 style='color: #00f2ff;'>✅ Shortlisted</h4>", unsafe_allow_html=True)
            short_data = c.execute("SELECT id, real_name, score FROM resumes WHERE category=? AND score >= 50", (role,)).fetchall()
            if not short_data: st.write("No data found for this role.")
            for cid, name, score in short_data:
                with st.container():
                    st.markdown(f"<div class='card-short'><b>{name}</b> ({score}%)</div>", unsafe_allow_html=True)
                    if st.button(f"SELECT {name.split()[0]}", key=f"sel_{cid}", use_container_width=True):
                        st.session_state['selected_name'] = name
                        st.session_state['selected_role'] = role
                        st.session_state['page'] = "📄 Job Offer"
                        st.rerun()

        with col_right:
            st.markdown("<h4 style='color: #ef4444;'>❌ Rejected</h4>", unsafe_allow_html=True)
            rej_data = c.execute("SELECT real_name, score FROM resumes WHERE category=? AND score < 50", (role,)).fetchall()
            if not rej_data: st.write("No rejections found.")
            for name, score in rej_data:
                st.markdown(f"<div class='card-reject'><b>{name}</b> ({score}%)</div>", unsafe_allow_html=True)

    # --- OTHER TABS ---
    elif st.session_state['page'] == "✅ Shortlisted":
        st.title("Master Shortlist")
        data = c.execute("SELECT real_name, category, score FROM resumes WHERE score >= 50").fetchall()
        st.table(data)

    elif st.session_state['page'] == "❌ Rejected":
        st.title("Master Rejection List")
        data = c.execute("SELECT real_name, category, score FROM resumes WHERE score < 50").fetchall()
        st.table(data)

    # --- JOB OFFER ---
    elif st.session_state['page'] == "📄 Job Offer":
        st.title("Generate Offer Letter")
        t_name = st.session_state.get('selected_name', "Candidate")
        t_role = st.session_state.get('selected_role', "Professional")
        
        if t_name == "Candidate":
            st.warning("Please go to 'Analyze & Results' and select a candidate first.")
        else:
            with st.container(border=True):
                st.markdown(f"### Preparing Offer for: <span style='color:#00f2ff'>{t_name}</span>", unsafe_allow_html=True)
                st.text_area("Body", f"Dear {t_name},\n\nWe are pleased to offer you the {t_role} position. Your skills matched our criteria.")
                if st.button("SEND OFFER"): st.success(f"Offer Letter Dispatched to {t_name}!")
                if st.button("BACK TO ANALYZER"):
                    st.session_state['page'] = "📤 Analyze & Results"
                    st.rerun()
