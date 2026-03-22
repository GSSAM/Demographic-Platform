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
import asyncio

# --- 1. إعدادات الواجهة (ألوان إحصائية احترافية) ---
st.set_page_config(page_title="مختبر التحليل الديموغرافي", page_icon="📈", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    :root { --primary-blue: #1a4e8a; }
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Cairo', sans-serif; direction: rtl; text-align: right;
    }
    .report-card {
        background: white; padding: 20px; border-right: 6px solid var(--primary-blue);
        border-radius: 12px; margin: 15px 0; box-shadow: 0 2px 15px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] { background-color: #0e2a47 !important; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. محرك الاتصال الماسي (نفس منطق BACFLIX) ---
async def call_gemini_smart(prompt):
    if "API_KEYS" not in st.secrets:
        st.error("مفاتيح API غير متوفرة.")
        return None
    keys = list(st.secrets["API_KEYS"])
    import random
    random.shuffle(keys)
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            return client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        except: continue
    return None

# --- 3. وظائف معالجة البيانات ---
@st.cache_data
def load_data_file(file_bytes, file_name):
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    try:
        if ext == 'sav': df, meta = pyreadstat.read_sav(tmp_path)
        else: df = pd.read_csv(tmp_path) if ext == 'csv' else pd.read_excel(tmp_path); meta = None
    finally: os.remove(tmp_path)
    return df, meta

# --- 4. الهيكل الرئيسي للمنصة ---
st.sidebar.markdown(f'<div style="text-align:center; color:white;"><h3>د. قاسم سمير</h3><p>المحلل الديموغرافي الذكي</p></div>', unsafe_allow_html=True) [cite: 8]

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات (SPSS, Excel, CSV)", type=['sav', 'csv', 'xlsx']) [cite: 5]

if uploaded_file:
    df, meta = load_data_file(uploaded_file.getvalue(), uploaded_file.name)
    
    st.title("🔬 مختبر التحليل الديموغرافي - BACFLIX")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الحالات", f"{df.shape[0]:,}") [cite: 17]
    col2.metric("المتغيرات", df.shape[1]) [cite: 13]
    col3.metric("الحالة", "متصل ✅") [cite: 14]

    if "messages" not in st.session_state: st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("اطلب جدولاً، رسماً، أو تحليلاً..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner('جاري معالجة طلبك بدقة...'):
                meta_dict = dict(zip(meta.column_names, meta.column_labels)) if meta else {}
                
                # تحديث التوجيهات لتكون مرنة (جداول + رسومات)
                prompt = f"""
                أنت أستاذ خبير في التحليل الإحصائي. البيانات في `df`. الأعمدة: {list(df.columns)}. القاموس: {meta_dict}.
                التعليمات:
                1. إذا طلب المستخدم "جدول" (Table): استخدم `pd.crosstab` أو `value_counts` مع `margins=True` للمجاميع، واعرضه بـ `st.dataframe`.
                2. إذا طلب المستخدم "رسم" أو "مخطط" (Chart/Plot): استخدم `px` (Plotly) واعرضه بـ `st.plotly_chart`.
                3. إذا طلب الاثنين: نفذ الاثنين معاً.
                4. اشرح النتائج بأسلوب أكاديمي أولاً ثم ضع الكود داخل ```python ... ```.
                السؤال: {user_query}
                """
                
                response = asyncio.run(call_gemini_smart(prompt))
                
                if response:
                    full_text = response.text
                    report_text = re.sub(r"```python.*?```", "", full_text, flags=re.DOTALL).strip()
                    code_match = re.search(r"```python(.*?)```", full_text, re.DOTALL)
                    
                    st.markdown(f'<div class="report-card">{report_text}</div>', unsafe_allow_html=True)
                    
                    if code_match:
                        exec_env = {'df': df, 'pd': pd, 'px': px, 'st': st, 'stats': stats, 
                                    'value_labels': getattr(meta, 'variable_value_labels', {}) if meta else {}}
                        try:
                            exec(code_match.group(1).strip(), exec_env)
                        except Exception as e: st.error(f"خطأ برمي: {e}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": report_text})
