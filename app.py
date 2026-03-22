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
from docx import Document
import random

# --- 1. إعدادات الواجهة الاحترافية (SPSS Style) ---
st.set_page_config(page_title="منصة التحليل الإحصائي والديموغرافي", page_icon="📊", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

:root {
    --stat-blue: #0F62FE; /* أزرق IBM/SPSS */
    --stat-dark: #121619;
    --stat-bg: #F4F7F6;
    --border-color: #E0E0E0;
}

html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label {
    font-family: 'Cairo', sans-serif;
    direction: rtl;
    text-align: right;
}

.stApp { background-color: var(--stat-bg); }

/* تنسيق الحاويات الرئيسية */
.main .block-container {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    border: 1px solid var(--border-color);
}

/* تنسيق الأزرار */
.stButton>button {
    background-color: var(--stat-blue);
    color: white;
    font-weight: 600;
    border-radius: 6px;
    border: none;
    padding: 0.6rem 1.2rem;
    width: 100%;
    transition: all 0.3s ease;
}
.stButton>button:hover { background-color: #0353E9; box-shadow: 0 4px 10px rgba(15,98,254,0.3); }

/* بطاقة التقرير الإحصائي */
.report-card {
    background: #ffffff;
    padding: 20px 25px;
    border-right: 5px solid var(--stat-blue);
    border-radius: 8px;
    margin: 15px 0;
    border: 1px solid var(--border-color);
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    line-height: 1.8;
    color: #333;
}

/* القائمة الجانبية */
[data-testid="stSidebar"] {
    background-color: var(--stat-dark) !important;
    color: white;
}
[data-testid="stSidebar"] * { color: white !important; }

/* معلومات المنشئ */
.creator-box {
    background: rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 20px;
}
.creator-box h3 { color: #6EA6FF !important; margin-bottom: 5px; font-weight: 700;}
.creator-box p { margin: 2px 0; font-size: 0.9rem; opacity: 0.9;}
</style>""", unsafe_allow_html=True)

# --- 2. وظائف المعالجة والتصدير ---
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

def export_to_word(text):
    doc = Document()
    doc.add_heading('التقرير الإحصائي - د. قاسم سمير', 0)
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # تنظيف علامات البولد مؤقتاً
    doc.add_paragraph(clean_text)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. محرك الاتصال الماسي (نظام الفشل الاحتياطي المتزامن) ---
def call_gemini_sync(prompt):
    if "API_KEYS" not in st.secrets:
        st.error("⚠️ مفاتيح API غير متوفرة في الخزنة السرية.")
        return None
    
    keys = list(st.secrets["API_KEYS"])
    random.shuffle(keys) # خلط عشوائي لتوزيع الضغط
    
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            return response.text
        except Exception:
            continue # تخطي الخطأ والانتقال للمفتاح التالي بسلاسة
    return None

def execute_safely(code, df, meta_dict):
    env = {'df': df.copy(), 'pd': pd, 'px': px, 'go': go, 'st': st, 'stats': stats, 'value_labels': meta_dict}
    try:
        exec(code, env)
        return True, None
    except Exception as e:
        return False, str(e)

# --- 4. القائمة الجانبية (Sidebar) ---
st.sidebar.markdown("""
<div class="creator-box">
    <h3>الدكتور قاسم سمير</h3>
    <p>تصميم وتطوير المنصة</p>
    <hr style="border-color: rgba(255,255,255,0.1); margin: 10px 0;">
    <p>📧 <a href="mailto:esa.gacem@univ-blida2.dz" style="color: #6EA6FF; text-decoration: none;">esa.gacem@univ-blida2.dz</a></p>
    <p>📞 0672595801</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### ⚙️ أدوات التحكم")
if st.sidebar.button("🧹 تصفير جلسة التحليل"):
    st.session_state.messages = []
    st.rerun()

st.sidebar.markdown("""
<div style="margin-top: 30px; font-size: 0.85rem; color: #aaa; text-align: center;">
    <p>مدعوم بخوارزميات الذكاء الاصطناعي والمحركات الإحصائية لتقديم أدق النتائج.</p>
</div>
""", unsafe_allow_html=True)


# --- 5. الواجهة الرئيسية ---
st.title("📊 منصة التحليل الإحصائي والديموغرافي")
st.markdown("<p style='color: #666; font-size: 1.1rem; margin-bottom: 2rem;'>حلول إحصائية متقدمة للباحثين وصناع القرار</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 قم برفع قاعدة البيانات للبدء (SPSS .sav, Excel .xlsx, CSV .csv)", type=['sav', 'csv', 'xlsx'])

if uploaded_file:
    df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
    meta_dict = dict(zip(meta.column_names, meta.column_labels)) if hasattr(meta, 'column_names') else {}
    
    # بطاقات المعلومات
    c1, c2, c3 = st.columns(3)
    c1.metric("📌 إجمالي الحالات (Rows)", f"{df.shape[0]:,}")
    c2.metric("📋 المتغيرات (Columns)", df.shape[1])
    c3.metric("🟢 حالة الخادم", "متصل وجاهز للتحليل")

    with st.expander("🔍 استكشاف البيانات ودليل المتغيرات", expanded=False):
        t1, t2 = st.tabs(["البيانات الخام", "دليل الأعمدة (Labels)"])
        with t1: st.dataframe(df.head(10), use_container_width=True)
        with t2: 
            if meta_dict:
                st.dataframe(pd.DataFrame({"المتغير": list(meta_dict.keys()), "الوصف": list(meta_dict.values())}), use_container_width=True)
            else:
                st.info("لا توجد أوصاف برمجية مرفقة في هذا الملف.")

    st.markdown("---")

    # نظام الدردشة الإحصائية
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if user_query := st.chat_input("✍️ اطلب جدولاً إحصائياً، رسماً بيانياً، أو اختباراً (مثال: ارسم توزيع المستوى المعيشي)..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🔄 جاري معالجة البيانات وبناء النماذج..."):
                prompt = f"""
                أنت خبير في الإحصاء وتحليل البيانات (Data Scientist). مهمتك تنفيذ استفسار المستخدم بدقة.
                البيانات موجودة في المتغير `df`. 
                قائمة الأعمدة: {list(df.columns)}
                دليل أوصاف المتغيرات: {meta_dict}

                التعليمات الصارمة:
                1. اكتب شرحاً وقراءة إحصائية للنتائج باللغة العربية بأسلوب أكاديمي دقيق.
                2. يجب وضع الكود البرمجي حصراً داخل علامات: ```python [الكود هنا] ```. 
                3. الكود يجب أن يتبع الشرح (الشرح أولاً ثم الكود).
                4. لعرض الجداول استخدم `st.dataframe()`. ولعرض الرسومات استخدم `st.plotly_chart(fig, use_container_width=True)` باستخدام `px` (Plotly).
                5. في جداول التقاطع `pd.crosstab` استخدم `margins=True, margins_name='المجموع'`.

                طلب المستخدم: {user_query}
                """
                
                response_text = call_gemini_sync(prompt)
                
                if response_text:
                    # فصل الشرح عن الكود بشكل آمن
                    report_text = re.sub(r"```python\s*.*?```", "", response_text, flags=re.DOTALL|re.IGNORECASE).strip()
                    code_matches = re.findall(r"```python\s*(.*?)```", response_text, re.DOTALL|re.IGNORECASE)
                    
                    if report_text:
                        st.markdown(f'<div class="report-card">{report_text}</div>', unsafe_allow_html=True)
                        st.download_button("📄 تحميل التقرير (Word)", data=export_to_word(report_text), file_name='Statistical_Report.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

                    if code_matches:
                        for code in code_matches:
                            success, error_msg = execute_safely(code.strip(), df, meta_dict)
                            if not success:
                                st.error(f"⚠️ حدث خطأ أثناء تنفيذ الرسوم أو الجداول: {error_msg}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    st.error("❌ نعتذر، تعذر الاتصال بالمحركات التحليلية. جميع المفاتيح استنفدت الرصيد.")
else:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; background: white; border-radius: 10px; border: 1px dashed #ccc; margin-top: 2rem;">
        <h2 style="color: #0F62FE;">مرحباً بك في منصتك التحليلية المستقلة</h2>
        <p style="color: #666; font-size: 1.1rem;">يرجى رفع قاعدة البيانات الخاصة بك في الأعلى للبدء في استكشاف وتحليل بياناتك بلمسة زر.</p>
    </div>
    """, unsafe_allow_html=True)
