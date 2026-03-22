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
        --primary-blue: #1a4e8a;
        --bg-light: #f4f7f9;
    }

    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }

    .stButton>button {
        width: 100%;
        background-color: var(--primary-blue);
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }

    .report-card {
        background: white;
        padding: 25px;
        border-right: 6px solid var(--primary-blue);
        border-radius: 12px;
        margin: 15px 0;
        box-shadow: 0 2px 15px rgba(0,0,0,0.05);
        color: #2c3e50;
    }

    [data-testid="stSidebar"] {
        background-color: #0e2a47 !important;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. محرك الاتصال الماسي ---
async def call_gemini_smart(prompt):
    if "API_KEYS" not in st.secrets:
        st.error("مفاتيح API غير متوفرة في الخزنة السرية.")
        return None
    
    keys = list(st.secrets["API_KEYS"])
    import random
    random.shuffle(keys)
    
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
<div style="text-align: center; padding: 10px;">
    <h3 style="color: white;">الدكتور قاسم سمير</h3>
    <p style="color: #ccc;">مختبر التحليل الإحصائي</p>
    <p style="font-size: 0.8em; color: #aaa;">0672595801</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🧹 تصفير المحادثة"):
    st.session_state.messages = []
    st.rerun()

st.title("🔬 المختبر الإحصائي الذكي")

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات (SPSS, Excel, CSV)", type=['sav', 'csv', 'xlsx'])

if uploaded_file:
    df, meta = load_data_file(uploaded_file.getvalue(), uploaded_file.name)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("عدد العينات", f"{df.shape[0]:,}")
    col2.metric("المتغيرات", df.shape[1])
    col3.metric("نوع الملف", uploaded_file.name.split('.')[-1].upper())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض تاريخ المحادثة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("اطلب تحليلاً إحصائياً أو رسماً بيانياً..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner('جاري التحليل وتوليد الرسوم...'):
                # جلب أسماء الأعمدة والأوصاف (Labels)
                meta_dict = {}
                if meta and hasattr(meta, 'column_names'):
                    meta_dict = dict(zip(meta.column_names, meta.column_labels))
                
                prompt = f"""
                أنت خبير إحصائي ديموغرافي. البيانات الحقيقية في `df`. الأعمدة: {list(df.columns)}. القاموس: {meta_dict}.
                التعليمات:
                1. استخدم مكتبة Plotly (px) حصراً للرسم.
                2. يجب أن ينتهي الكود دائماً بـ `st.plotly_chart(fig, use_container_width=True)`.
                3. اشرح النتائج بأسلوب أكاديمي في بداية الرد.
                4. ضع الكود البرمجي في نهاية الرد داخل ```python ... ```.
                السؤال: {user_query}
                """
                
                response = asyncio.run(call_gemini_smart(prompt))
                
                if response:
                    full_text = response.text
                    
                    # 1. استخراج الشرح (النص خارج كود بايثون)
                    report_text = re.sub(r"```python.*?```", "", full_text, flags=re.DOTALL).strip()
                    
                    # 2. استخراج الكود البرمجي
                    code_match = re.search(r"```python(.*?)```", full_text, re.DOTALL)
                    
                    # عرض الشرح في بطاقة أنيقة
                    st.markdown(f'<div class="report-card">{report_text}</div>', unsafe_allow_html=True)
                    
                    # تنفيذ الكود لعرض الرسم البياني
                    if code_match:
                        code_to_exec = code_match.group(1).strip()
                        exec_env = {
                            'df': df.copy(),
                            'pd': pd,
                            'px': px,
                            'st': st,
                            'stats': stats,
                            'value_labels': getattr(meta, 'variable_value_labels', {}) if meta else {}
                        }
                        try:
                            # تنفيذ كود الرسم
                            exec(code_to_exec, exec_env)
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء توليد الرسم: {e}")
                    
                    # حفظ الرد في التاريخ
                    st.session_state.messages.append({"role": "assistant", "content": report_text})
                else:
                    st.error("فشل الاتصال بالمحرك الذكي.")
else:
    st.info("👋 يرجى رفع ملف البيانات للبدء.")
