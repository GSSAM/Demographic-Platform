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
import numpy as np
import asyncio

# --- 1. إعدادات الواجهة (نمط SPSS الاحترافي) ---
st.set_page_config(page_title="SPSS Analytics Pro", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    :root {
        --spss-blue: #0F62FE;
        --spss-dark: #161616;
        --spss-light: #F4F4F4;
        --spss-border: #E0E0E0;
    }
    
    * {
        font-family: 'Cairo', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main .block-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    /* نمط أزرار SPSS */
    .stButton>button {
        background: linear-gradient(90deg, #0F62FE 0%, #0353E9 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(15, 98, 254, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(15, 98, 254, 0.4);
    }
    
    /* Sidebar بنمط SPSS */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161616 0%, #262626 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* جداول البيانات */
    .dataframe {
        border: 2px solid var(--spss-border) !important;
        border-radius: 8px;
        overflow: hidden;
    }
    
    .dataframe thead th {
        background: linear-gradient(90deg, #0F62FE 0%, #0353E9 100%) !important;
        color: white !important;
        font-weight: 600;
        padding: 12px !important;
        text-align: right !important;
    }
    
    .dataframe tbody tr:nth-child(even) {
        background: #F8F9FA;
    }
    
    /* صندوق التقرير */
    .report-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 12px;
        border-right: 6px solid #0F62FE;
        box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        margin: 1.5rem 0;
        direction: rtl;
        text-align: right;
    }
    
    .report-box h1, .report-box h2, .report-box h3 {
        color: #0F62FE;
        margin-top: 1.5rem;
    }
    
    /* مقاييس SPSS */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #0F62FE;
    }
    
    /* حقل الإدخال */
    .stChatInput {
        border: 2px solid #0F62FE;
        border-radius: 10px;
    }
    
    /* رسائل الدردشة */
    .stChatMessage {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* شريط التحميل */
    .stSpinner > div {
        border-top-color: #0F62FE !important;
    }
    
    /* عناوين الأقسام */
    h1, h2, h3 {
        color: #161616;
        font-weight: 700;
    }
    
    /* أيقونات الحالة */
    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-success {
        background: #24A148;
        color: white;
    }
    
    .status-warning {
        background: #F1C21B;
        color: #161616;
    }
    
    /* تحسين عرض الأكواد */
    .stCodeBlock {
        background: #f6f8fa;
        border-radius: 8px;
        border: 1px solid #d0d7de;
    }
    
    /* تحسين الـ expander */
    .streamlit-expanderHeader {
        background: #f6f8fa;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. وظائف المعالجة الذكية للملفات ---
class MockMeta:
    def __init__(self, columns):
        self.column_names = columns
        self.column_labels = columns
        self.variable_value_labels = {}

@st.cache_data
def load_data(file_bytes, file_name):
    """تحميل البيانات من ملفات مختلفة"""
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        if ext == 'sav':
            df, meta = pyreadstat.read_sav(tmp_path)
        elif ext == 'csv':
            df = pd.read_csv(tmp_path)
            meta = MockMeta(df.columns.tolist())
        else:
            df = pd.read_excel(tmp_path)
            meta = MockMeta(df.columns.tolist())
    finally:
        os.remove(tmp_path)
    return df, meta

# --- 3. نظام الاتصال بـ Gemini مع Failover ---
def get_api_keys():
    """جلب مفاتيح API من Secrets"""
    if "API_KEYS" not in st.secrets:
        st.error("⚠️ لم يتم العثور على مفاتيح API في الإعدادات السرية")
        return []
    return st.secrets["API_KEYS"]

async def call_gemini_with_failover(prompt):
    """استدعاء Gemini مع نظام Failover للمفاتيح"""
    keys = get_api_keys()
    if not keys:
        return None
    
    import random
    random.shuffle(keys)  # خلط المفاتيح لتوزيع الحمل
    
    target_model = "gemini-2.0-flash-exp"
    
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=target_model,
                contents=prompt
            )
            return response
        except Exception as e:
            continue  # الانتقال للمفتاح التالي
    return None

# --- 4. دوال التنفيذ الآمن للأكواد ---
def safe_execute_code(code, df):
    """تنفيذ آمن للكود مع التقاط النتائج"""
    exec_env = {
        'df': df.copy(),
        'pd': pd,
        'np': np,
        'st': st,
        'px': px,
        'go': go,
        'stats': stats,
    }
    
    try:
        # تنفيذ الكود
        exec(code, exec_env)
        return True, None
    except Exception as e:
        return False, str(e)

# --- 5. واجهة المستخدم الرئيسية ---

# Sidebar
st.sidebar.markdown("""
<div style="text-align: center; padding: 1.5rem;">
    <h1 style="color: #0F62FE; font-size: 2.5rem; margin: 0;">📊</h1>
    <h2 style="margin: 0.5rem 0; font-size: 1.5rem;">SPSS Analytics Pro</h2>
    <div style="height: 3px; background: linear-gradient(90deg, #0F62FE, #0353E9); margin: 1rem 0;"></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 10px; margin: 1rem 0;">
    <h4 style="color: #0F62FE; margin: 0 0 0.5rem 0;">👨‍🏫 أ. قاسم سمير</h4>
    <p style="margin: 0.3rem 0; font-size: 0.9rem;">📊 إحصاء وتحليل ديموغرافي</p>
    <p style="margin: 0.3rem 0; font-size: 0.9rem;">📱 0672595801</p>
</div>
""", unsafe_allow_html=True)

# زر مسح الذاكرة
if st.sidebar.button("🧹 مسح الذاكرة والبدء من جديد", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# معلومات إضافية في Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
    <h4 style="color: #0F62FE; font-size: 0.9rem;">📌 الإمكانيات المتاحة:</h4>
    <ul style="font-size: 0.85rem; line-height: 1.8;">
        <li>التحليل الوصفي الشامل</li>
        <li>الاختبارات الإحصائية</li>
        <li>الرسوم البيانية التفاعلية</li>
        <li>جداول التكرار والتوزيع</li>
        <li>تحليل الارتباط والانحدار</li>
        <li>اختبار الفرضيات</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# العنوان الرئيسي
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 2.5rem; margin: 0; background: linear-gradient(90deg, #0F62FE, #0353E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🔬 المختبر الإحصائي الذكي
    </h1>
    <p style="color: #666; font-size: 1.1rem; margin-top: 0.5rem;">نظام تحليل بيانات متقدم بتقنية الذكاء الاصطناعي</p>
</div>
""", unsafe_allow_html=True)

# رفع الملف
uploaded_file = st.file_uploader(
    "📂 ارفع ملف البيانات",
    type=['sav', 'csv', 'xlsx'],
    help="يدعم ملفات SPSS (.sav) و Excel (.xlsx) و CSV"
)

if uploaded_file:
    # تحميل البيانات
    df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
    
    # عرض إحصائيات سريعة
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 إجمالي الحالات", f"{df.shape[0]:,}")
    with col2:
        st.metric("📊 عدد المتغيرات", df.shape[1])
    with col3:
        missing_count = df.isnull().sum().sum()
        st.metric("🔢 القيم الناقصة", f"{missing_count:,}")
    with col4:
        st.markdown('<div style="text-align: center; padding-top: 10px;"><span class="status-badge status-success">✅ متصل بالسحابة</span></div>', unsafe_allow_html=True)
    
    # عرض معاينة البيانات
    with st.expander("👁️ معاينة البيانات (أول 10 سجلات)", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)
    
    # عرض معلومات المتغيرات
    with st.expander("📋 معلومات المتغيرات", expanded=False):
        var_info = pd.DataFrame({
            'المتغير': df.columns,
            'النوع': df.dtypes.astype(str),
            'القيم الفريدة': [df[col].nunique() for col in df.columns],
            'القيم الناقصة': [df[col].isnull().sum() for col in df.columns],
            'نسبة الاكتمال': [f"{(1 - df[col].isnull().sum()/len(df))*100:.1f}%" for col in df.columns]
        })
        st.dataframe(var_info, use_container_width=True)
    
    st.markdown("---")
    
    # نظام الدردشة المطور
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # عرض الرسائل السابقة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"], unsafe_allow_html=True)
    
    # حقل الإدخال
    user_query = st.chat_input("✍️ اكتب طلبك هنا... (مثال: احسب المتوسط الحسابي لمتغير العمر، أو ارسم رسماً بيانياً للتوزيع)")
    
    if user_query:
        # إضافة رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner('🔄 جاري التحليل والتنفيذ...'):
                # إعداد البيانات الوصفية
                meta_dict = dict(zip(meta.column_names, meta.column_labels))
                df_info = {
                    'columns': list(df.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'shape': df.shape,
                    'sample': df.head(3).to_dict()
                }
                
                # Prompt محسّن للتنفيذ الفعلي
                full_prompt = f"""
أنت محلل إحصائي خبير متخصص في SPSS وتحليل البيانات. مهمتك تنفيذ التحليلات المطلوبة بدقة عالية.

**البيانات المتاحة:**
- الأعمدة: {df_info['columns']}
- عدد السجلات: {df_info['shape'][0]}
- عدد المتغيرات: {df_info['shape'][1]}
- أنواع البيانات: {df_info['dtypes']}

**تعليمات التنفيذ الصارمة:**

1. **الكود يجب أن يكون قابل للتنفيذ 100%** - لا تكتب كود وهمي
2. ضع الكود داخل: ```python ... ```
3. المتغيرات المتاحة في البيئة:
   - df: DataFrame الرئيسي
   - pd, np, st, px, go, stats: مكتبات جاهزة

4. **للإحصائيات الوصفية:**
```python
# مثال: حساب المتوسط
mean_value = df['column_name'].mean()
st.metric("المتوسط الحسابي", f"{{mean_value:.2f}}")
