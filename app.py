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

# --- 1. إعدادات الواجهة (مستوحاة من تصميم BACFLIX) ---
st.set_page_config(page_title=" مختبر التحليل الديموغرافي", page_icon="📈", layout="wide")

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
    .stButton>button { 
        background: #E50914; color: white; font-weight: bold; 
        border-radius: 6px; transition: 0.3s; border: none;
    }
    .stButton>button:hover { background: #b80710; transform: translateY(-2px); }
    .report-box { 
        background: white; color: #111; padding: 2cm; 
        border-radius: 4px; font-family: 'Amiri', serif; 
        font-size: 18px; line-height: 2; border-right: 5px solid #E50914;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content { background: #161b22; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. وظائف المعالجة الذكية للملفات ---
class MockMeta:
    def __init__(self, columns):
        self.column_names = columns; self.column_labels = columns; self.variable_value_labels = {}

@st.cache_data
def load_data(file_bytes, file_name):
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    try:
        if ext == 'sav': df, meta = pyreadstat.read_sav(tmp_path)
        elif ext == 'csv': df, meta = pd.read_csv(tmp_path), MockMeta(pd.read_csv(tmp_path).columns.tolist())
        else: df, meta = pd.read_excel(tmp_path), MockMeta(pd.read_excel(tmp_path).columns.tolist())
    finally:
        os.remove(tmp_path)
    return df, meta

# --- 3. نظام الاتصال الماسي (مستنسخ من BACFLIX) ---
# سيتم جلب المفاتيح من Secrets السيرفر كما في النسخة السابقة لضمان الأمان
def get_api_client():
    if "API_KEYS" not in st.secrets:
        st.error("⚠️ لم يتم العثور على مفاتيح API في الخزنة السرية (Secrets).")
        return None
    return st.secrets["API_KEYS"]

async def call_gemini_with_failover(prompt):
    keys = get_api_client()
    if not keys: return None
    
    import random
    random.shuffle(keys) # خلط المفاتيح لتوزيع الضغط كما في كود BACFLIX
    
    target_model = "gemini-2.5-flash" # الموديل الموحد
    
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(model=target_model, contents=prompt)
            return response
        except Exception:
            continue # الانتقال للمفتاح التالي في حالة الفشل
    return None

# --- 4. واجهة المستخدم الرئيسية ---
st.sidebar.title("📈 المحلل الديموغرافي")
st.sidebar.markdown(f"""
<div class="credits-box">
        <h4>👨‍💻 تصميم وتطوير المنصة</h4>
        <h3>الدكتور قاسم سمير</h3>
        <p>📧 <a href="mailto:esa.gacem@univ-blida2.dz" style="color: #ffdd57;">esa.gacem@univ-blida2.dz</a></p>
        <p>📞 0672595801</p>
    </div>
""", unsafe_allow_html=True)

if st.sidebar.button("🧹 مسح الذاكرة"):
    st.session_state.messages = []
    st.rerun()

st.title("🔬 المختبر الديموغرافي الذكي - BACFLIX")

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات (SPSS, Excel, CSV)", type=['sav', 'csv', 'xlsx'])

if uploaded_file:
    df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
    
    # عرض إحصائيات سريعة
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الحالات", f"{df.shape[0]:,}")
    col2.metric("المتغيرات", df.shape[1])
    col3.metric("الحالة", "متصل بالسحابة ✅")

    # نظام الدردشة المطور
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("✍️ اطلب تحليلاً إحصائياً أو رسماً بيانياً..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner('جاري الاتصال بمحرك 2.5 Flash وتوليد التحليل...'):
                meta_dict = dict(zip(meta.column_names, meta.column_labels))
                
                # توجيهات الأستاذ قاسم سمير الصارمة للموديل
                full_prompt = f"""
                أنت أستاذ خبير في التحليل الإحصائي والديموغرافي.
                استخدم البيانات الحقيقية في `df`. الأعمدة: {list(df.columns)}. القاموس: {meta_dict}.
                
                التعليمات:
                1. طبق اختبارات الدلالة الإحصائية (P-value) عند المقارنة.
                2. استخدم Plotly (px) للرسوم التفاعلية.
                3. في جداول التكرار، أضف المجموع إجبارياً (margins=True).
                4. استخدم LaTeX للمعادلات الإحصائية.
                5. الكود يجب أن يكون داخل ```python ... ```.
                
                السؤال: {user_query}
                """
                
                # استخدام دالة الـ Failover الماسية
                import asyncio
                response = asyncio.run(call_gemini_with_failover(full_prompt))
                
                if response:
                    full_text = response.text
                    report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                    code_match = re.search(r"`{3}(?:python)?\s*(.*?)\s*`{3}", full_text, re.DOTALL | re.IGNORECASE)
                    
                    st.markdown(f'<div class="report-box">{report_text}</div>', unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": report_text})

                    if code_match:
                        exec_env = globals().copy()
                        exec_env.update({'df': df.copy(), 'pd': pd, 'st': st, 'px': px, 'stats': stats, 'value_labels': getattr(meta, 'variable_value_labels', {})})
                        try:
                            exec(code_match.group(1).strip(), exec_env)
                        except Exception as e:
                            st.error(f"خطأ في التنفيذ: {e}")
                else:
                    st.error("❌ فشل الاتصال بجميع المفاتيح. يرجى التحقق من القوطة.")

else:
    st.info("👋 مرحباً بك في مختبر BACFLIX. يرجى رفع ملف البيانات للبدء في التحليل الإحصائي.")
