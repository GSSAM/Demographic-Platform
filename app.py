import streamlit as st
from google import genai
import pandas as pd
import pyreadstat
import tempfile
import os
import re
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as stats
import numpy as np
import asyncio
import random

# --- 1. إعدادات الواجهة الاحترافية ---
st.set_page_config(page_title="المختبر الإحصائي الذكي", page_icon="📊", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
:root{--spss-blue:#0F62FE;--spss-dark:#161616;}
*{font-family:'Cairo',sans-serif;}
.stApp{background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}
.main .block-container{background:white;padding:2rem;border-radius:15px;box-shadow:0 10px 40px rgba(0,0,0,0.1);}
.stButton>button{background: #0F62FE; color:white; border-radius:8px; font-weight:600; width:100%;}
.report-box{background:#f8f9fa; padding:1.5rem; border-right:6px solid #0F62FE; border-radius:8px; margin:1rem 0; direction:rtl; text-align:right;}
</style>""", unsafe_allow_html=True)

# --- 2. وظائف المعالجة ---
class MockMeta:
    def __init__(self, columns):
        self.column_names = columns; self.column_labels = columns; self.variable_value_labels = {}

@st.cache_data
def load_data(file_bytes, file_name):
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
        tmp.write(file_bytes); tmp_path = tmp.name
    try:
        if ext == 'sav': df, meta = pyreadstat.read_sav(tmp_path)
        elif ext == 'csv': df, meta = pd.read_csv(tmp_path), MockMeta(pd.read_csv(tmp_path).columns.tolist())
        else: df, meta = pd.read_excel(tmp_path), MockMeta(pd.read_excel(tmp_path).columns.tolist())
    finally: os.remove(tmp_path)
    return df, meta

async def call_gemini(prompt):
    if "API_KEYS" not in st.secrets: return None
    keys = list(st.secrets["API_KEYS"])
    random.shuffle(keys)
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            # تم التحديث لموديل أكثر استقراراً في البرمجة
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response
        except: continue
    return None

def safe_exec(code, df):
    # بيئة التنفيذ مع كل المكتبات اللازمة
    env = {'df': df, 'pd': pd, 'np': np, 'st': st, 'px': px, 'go': go, 'stats': stats}
    try:
        exec(code, env)
        return True, None
    except Exception as e: return False, str(e)

# --- 3. التوجيه المطور (الحل الجذري للمشكلة) ---
def make_prompt(query, cols, meta_dict):
    return f"""
أنت مبرمج بايثون ومحلل إحصائي محترف. مهمتك هي الإجابة على استفسارات المستخدم حول البيانات.
البيانات المتاحة: DataFrame باسم `df`. 
الأعمدة وأوصافها: {meta_dict}

التعليمات الصارمة:
1. إذا طلب المستخدم (رسم، مخطط، توزيع، علاقة، مقارنة) يجب أن تكتب كود Plotly فوراً.
2. استخدم `st.plotly_chart(fig, use_container_width=True)` لعرض الرسوم.
3. استخدم `st.dataframe()` لعرض الجداول.
4. يجب وضع الكود حصراً داخل علامات الكود: ```python [الكود هنا] ```.
5. لا تشرح الكود، بل اشرح "النتائج الإحصائية" باللغة العربية بأسلوب الدكتور قاسم سمير.
6. أضف `margins=True` في جداول التقاطع `pd.crosstab`.

السؤال: {query}
"""

# --- 4. واجهة المستخدم ---
st.sidebar.markdown(f"""<div style="text-align:center; background:#161616; padding:20px; border-radius:10px;">
<h2 style="color:#0F62FE;">أ. قاسم سمير</h2>
<p style="color:white; font-size:0.8rem;">إحصاء وتحليل ديموغرافي</p>
<p style="color:white; font-size:0.8rem;">0672595801</p>
</div>""", unsafe_allow_html=True) [cite: 8, 29]

if st.sidebar.button("🧹 مسح الذاكرة"):
    st.session_state.messages = []; st.rerun()

st.title("🔬 المختبر الإحصائي الذكي") [cite: 3, 4]

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات", type=['sav', 'csv', 'xlsx']) [cite: 5]

if uploaded_file:
    df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 الحالات", str(df.shape[0])) [cite: 17]
    col2.metric("📊 المتغيرات", str(df.shape[1])) [cite: 13]
    col3.metric("الحالة", "متصل ✅") [cite: 14]

    if "messages" not in st.session_state: st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("✍️ اكتب طلبك هنا (مثلاً: ارسم توزيع المستوى المعيشي)..."): [cite: 19]
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🔄 جاري التحليل والتنفيذ..."):
                m_dict = dict(zip(meta.column_names, meta.column_labels)) if meta else {}
                prompt = make_prompt(user_query, list(df.columns), m_dict)
                response = asyncio.run(call_gemini(prompt))
                
                if response:
                    full_text = response.text
                    # نمط البحث عن الكود أصبح أكثر مرونة (يعالج وجود أو عدم وجود مسافات/سطور)
                    code_pattern = r"```python\s*(.*?)```"
                    code_matches = re.findall(code_pattern, full_text, re.DOTALL)
                    report_text = re.sub(r"```python.*?```", "", full_text, flags=re.DOTALL).strip()
                    
                    if report_text:
                        st.markdown(f'<div class="report-box">{report_text}</div>', unsafe_allow_html=True)
                    
                    if code_matches:
                        for code in code_matches:
                            ok, err = safe_exec(code.strip(), df)
                            if not ok: st.error(f"⚠️ خطأ تقني: {err}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                else:
                    st.error("❌ فشل الاتصال.")
