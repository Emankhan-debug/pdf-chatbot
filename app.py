import streamlit as st
import PyPDF2
import io
from groq import Groq
from datetime import datetime
import sqlite3

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="PDF Chatbot",
    page_icon="📄",
    layout="centered"
)

# ================================
# CUSTOM CSS
# ================================
st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    .user-message {
        background-color: #1e3a5f;
        color: #e2e8f0;
        padding: 12px 16px;
        border-radius: 12px 0px 12px 12px;
        margin: 8px 0;
        margin-left: 20%;
        font-size: 14px;
        line-height: 1.5;
    }
    .bot-message {
        background-color: #1e293b;
        color: #cbd5e1;
        padding: 12px 16px;
        border-radius: 0px 12px 12px 12px;
        margin: 8px 0;
        margin-right: 20%;
        font-size: 14px;
        line-height: 1.5;
        border-left: 3px solid #6366f1;
    }
    .pdf-info {
        background-color: #1e293b;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 3px solid #22c55e;
        color: #86efac;
        font-size: 13px;
        margin: 8px 0;
    }
    .stButton button {
        background-color: #6366f1 !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ================================
# API KEY
# ================================
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    API_KEY = " "

client = Groq(api_key=API_KEY)


# ================================
# DATABASE
# ================================
def init_db():
    conn = sqlite3.connect("pdf_chat_history.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_name TEXT,
            role TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(pdf_name, role, message):
    conn = sqlite3.connect("pdf_chat_history.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (pdf_name, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (pdf_name, role, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

# ================================
# PDF READING FUNCTION
# ================================
def read_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
    text = ""
    for page_num, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text()
        if page_text:
            text += f"\n[Page {page_num + 1}]\n{page_text}"
    return text, len(pdf_reader.pages)

# ================================
# AI FUNCTION
# ================================
def get_ai_response(question, pdf_text, chat_history):
    system_prompt = f"""You are a helpful assistant that answers questions 
    based on the provided PDF document content.
    
    IMPORTANT RULES:
    - Only answer based on the PDF content provided
    - If the answer is not in the PDF, say "I couldn't find this in the document"
    - Always mention which page the information came from when possible
    - Be concise and clear
    
    PDF CONTENT:
    {pdf_text[:4000]}
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    for human, ai in chat_history[-3:]:
        messages.append({"role": "user", "content": human})
        messages.append({"role": "assistant", "content": ai})
    
    messages.append({"role": "user", "content": question})
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=500,
        temperature=0.3
    )
    return response.choices[0].message.content

# ================================
# INITIALIZE
# ================================
init_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""

# ================================
# UI
# ================================
st.markdown("""
<div style='text-align:center; padding: 20px 0'>
    <h1 style='color:#e2e8f0'>📄 PDF Chatbot</h1>
    <p style='color:#94a3b8'>Upload any PDF and ask questions from it</p>
</div>
""", unsafe_allow_html=True)

# PDF Upload
uploaded_file = st.file_uploader(
    "Upload your PDF",
    type="pdf",
    help="Upload any PDF file to start chatting"
)

if uploaded_file:
    if uploaded_file.name != st.session_state.pdf_name:
        with st.spinner("Reading PDF..."):
            pdf_text, num_pages = read_pdf(uploaded_file)
            st.session_state.pdf_text = pdf_text
            st.session_state.pdf_name = uploaded_file.name
            st.session_state.chat_history = []

    st.markdown(f"""
    <div class="pdf-info">
        ✅ PDF loaded: <strong>{st.session_state.pdf_name}</strong>
        — Now ask any question!
    </div>
    """, unsafe_allow_html=True)

    # Show chat history
    for human_msg, ai_msg in st.session_state.chat_history:
        st.markdown(f'<div class="user-message">👤 {human_msg}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="bot-message">📄 {ai_msg}</div>',
                    unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        question = st.text_input(
            "question",
            placeholder="Ask anything about your PDF...",
            label_visibility="collapsed"
        )
        submit = st.form_submit_button("Ask ➤")

    if submit and question:
        with st.spinner("Reading document..."):
            answer = get_ai_response(
                question,
                st.session_state.pdf_text,
                st.session_state.chat_history
            )
            st.session_state.chat_history.append((question, answer))
            save_message(st.session_state.pdf_name, "user", question)
            save_message(st.session_state.pdf_name, "assistant", answer)
            st.rerun()

    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

else:
    st.markdown("""
    <div style='text-align:center; padding:40px; color:#475569'>
        <h3>👆 Upload a PDF to get started</h3>
        <p>Works with any PDF — books, contracts, menus, manuals</p>
    </div>
    """, unsafe_allow_html=True)