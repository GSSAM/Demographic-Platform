import streamlit as st
from google import genai
import pandas as pd
import pyreadstat
import tempfile
import os
import re
from io import BytesIO
import plotly.express as px
import scipy.stats as stats
from docx import Document
import asyncio

# --- 1. إعدادات الواجهة الاحترافية (ستايل إحصائي + متوافق مع الجوال) ---
st.set_page_config(page_title="المختبر الديموغرافي الذكي", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    :root {
        --primary-blue: #1a4e8a; /* أزرق إحصائي رصين */
        --accent-gold: #f1c40f;
        --bg-light: #f4f7f9;
    }

    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }

    /* تحسين الواجهة للجوال */
    @media (max-width: 640px) {
        .main .block-container { padding: 10px !important; }
        .stMetric { margin-bottom: 10px !important; }
    }

    /* تصميم أزرار التحليل */
    .stButton>button {
        width: 100%;
        background-color: var(--primary-blue);
        color: white;
        border-radius: 8px;
        padding: 0.6rem;
        border: none;
        transition: 0.3s;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #12365f;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* ورقة النتائج الأكاديمية */
    .report-card {
        background: white;
        padding: 25px;
        border-right: 6px solid var(--primary-blue);
        border-radius: 12px;
        margin: 15px 0;
        box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        color: #2c3e50;
        line-height: 1.8;
    }

    /* القائمة الجانبية */
    [data-testid="stSidebar"] {
        background-color: #0e2a47 !important;
        color: white;
    }
    
    .sidebar-info {
        background: rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. محرك الاتصال الماسي (نفس منطق BACFLIX الاحترافي) ---
async def call_gemini_smart(prompt):
    if "API_KEYS" not in st.secrets:
        st.error("مفاتيح API غير متوفرة في الخزنة السرية.")
        return None
    
    keys = list(st.secrets["API_KEYS"])
    import random
    random.shuffle(keys) # خلط المفاتيح عشوائياً لتوزيع الضغط
    
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return response
        except Exception:
            continue
    return None

# --- 3. وظائف معالجة البيانات ---
@st.cache_data
def load_data_file(file_bytes, file_name):
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    try:
        if ext == 'sav': df, meta = pyreadstat.read_sav(tmp_path)
        elif ext == 'csv': df = pd.read_csv(tmp_path); meta = None
        else: df = pd.read_excel(tmp_path); meta = None
    finally:
        os.remove(tmp_path)
    return df, meta

# --- 4. الهيكل الرئيسي للمنصة ---
st.sidebar.markdown(f"""
<div class="sidebar-info">
    <h3 style="color: white; margin-bottom:5px;">الدكتور قاسم سمير</h3>
    <p style="font-size: 0.9em; opacity: 0.8;">مختبر التحليل الإحصائي</p>
    <hr style="border-color: rgba(255,255,255,0.2);">
    <p style="font-size: 0.8em;">📧 esa.gacem@univ-blida2.dz</p>
    <p style="font-size: 0.8em;">📞 0672595801</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🧹 تصفير المحادثة"):
    st.session_state.messages = []
    st.rerun()

st.title("🔬 المختبر الإحصائي الذكي")
st.caption("تحليل ديموغرافي متقدم مدعوم بالذكاء الاصطناعي - متوافق مع كافة الأجهزة")

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات (SPSS, Excel, CSV)", type=['sav', 'csv', 'xlsx'])

if uploaded_file:
    df, meta = load_data_file(uploaded_file.getvalue(), uploaded_file.name)
    
    # بطاقات البيانات (تتجاوب في الجوال)
    col1, col2, col3 = st.columns([1,1,1])
    col1.metric("عدد العينات", f"{df.shape[0]:,}")
    col2.metric("المتغيرات", df.shape[1])
    col3.metric("نوع الملف", uploaded_file.name.split('.')[-1].upper())

    with st.expander("🔍 معاينة سريعة للبيانات والأعمدة"):
        st.dataframe(df.head(5), use_container_width=True)

    # نظام الدردشة الإحصائية
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("اسأل المساعد عن أي تحليل إحصائي..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner('جاري التحليل الإحصائي...'):
                meta_info = str(list(df.columns))
                prompt = f"""
                أنت خبير إحصائي ديموغرافي. استخدم البيانات الحقيقية في `df`. الأعمدة: {meta_info}.
                التعليمات:
                1. استخدم Plotly (px) للرسوم التفاعلية (مهم جداً للجوال).
                2. أضف دائماً "المجموع" في الجداول الإحصائية.
                3. اشرح النتائج بأسلوب أكاديمي رصين.
                4. الكود البرمجي ضعه داخل ```python ... ```.
                السؤال: {user_query}
                """
                
                response = asyncio.run(call_gemini_smart(prompt))
                
                if response:
                    full_text = response.text
                    report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                    code_match = re.search(r"`{3}(?:python)?\s*(.*?)\s*`{3}", full_text, re.DOTALL | re.IGNORECASE)
                    
                    st.markdown(f'<div class="report-card">{report_text}</div>', unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": report_text})

                    if code_match:
                        exec_env = globals().copy()
                        exec_env.update({'df': df.copy(), 'pd': pd, 'st': st, 'px': px, 'stats': stats})
                        try:
                            exec(code_match.group(1).strip(), exec_env)
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء الرسم البياني: {e}")
                else:
                    st.error("فشل الاتصال بمحركات الذكاء الاصطناعي. يرجى المحاولة لاحقاً.")
else:
    st.info("👋 مرحباً بك دكتور قاسم. يرجى رفع ملف البيانات لفتح المختبر.")
