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

# --- 1. إعدادات الواجهة المتقدمة ---
st.set_page_config(page_title="المنصة الذكية للتحليل الديموغرافي", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, .stDataFrame {
        font-family: 'Cairo', sans-serif; direction: rtl; text-align: right;
    }
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 10px; font-weight: bold; margin-top: 5px; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#2e7bcf); color: white; }
    .report-box { background-color: #ffffff; padding: 25px; border-right: 6px solid #28a745; border-radius: 8px; margin: 15px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.05); font-size: 16px; line-height: 1.8;}
    .credits-box { background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-top: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)

# --- 2. وظائف المعالجة والتصدير ---
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
        elif ext in ['xlsx', 'xls']: df, meta = pd.read_excel(tmp_path), MockMeta(pd.read_excel(tmp_path).columns.tolist())
        else: raise ValueError("صيغة غير مدعومة")
    finally:
        os.remove(tmp_path)
    return df, meta

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=True, sheet_name='النتائج')
    return output.getvalue()

def to_word(text):
    doc = Document()
    doc.add_heading('التقرير الاستشاري - المنصة الذكية للتحليل الديموغرافي', 0)
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # تنظيف مبدئي للتنسيق
    doc.add_paragraph(clean_text)
    output = BytesIO()
    doc.save(output)
    return output.getvalue()

# --- 3. إدارة المفاتيح والقائمة الجانبية ---
api_keys = []
with st.sidebar:
    st.title("⚙️ حالة النظام")
    if "API_KEYS" in st.secrets:
        api_keys = st.secrets["API_KEYS"]
        st.success(f"✅ متصل بالسيرفر ({len(api_keys)} مفتاح)")
    else:
        st.warning("الخزنة السرية غير متوفرة. أدخل المفاتيح:")
        api_keys_input = st.text_area("مفاتيح API:", type="password", height=100)
        api_keys = [k.strip() for k in api_keys_input.replace(',', '\n').split('\n') if k.strip()]
        
    st.markdown("""
    <div class="credits-box">
        <h4>👨‍💻 تصميم وتطوير المنصة</h4>
        <h3>الدكتور قاسم سمير</h3>
        <p>📧 <a href="mailto:esa.gacem@univ-blida2.dz" style="color: #ffdd57;">esa.gacem@univ-blida2.dz</a></p>
        <p>📞 0672595801</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    if st.button("🧹 مسح محادثة المساعد"):
        st.session_state.messages = [{"role": "assistant", "content": "مرحباً دكتور قاسم! ارفع ملفك وسأقوم بتقديم ملخص تنفيذي فوراً 📊"}]
        st.session_state.auto_eda_done = False
        st.rerun()

# --- 4. الجزء الرئيسي ---
st.title("💎 المنصة الذكية للتحليل الديموغرافي والإحصائي المتقدم")

if api_keys:
    target_model = 'gemini-2.5-flash'
    uploaded_file = st.file_uploader("📂 ارفع قاعدة البيانات (sav, csv, xlsx)", type=['sav', 'csv', 'xlsx', 'xls'])
    
    df, meta = None, None
    if uploaded_file:
        df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
        c1, c2, c3 = st.columns(3)
        c1.metric("عدد الحالات", f"{df.shape[0]:,}")
        c2.metric("عدد المتغيرات", df.shape[1])
        c3.metric("المحرك الذكي", "Gemini 2.5 Pro Analytics")

        with st.expander("🔍 تصفح البيانات الخام ودليل المتغيرات", expanded=False):
            tab1, tab2 = st.tabs(["البيانات", "الدليل"])
            with tab1: st.dataframe(df.head(10), use_container_width=True)
            with tab2: st.dataframe(pd.DataFrame({"العمود": meta.column_names, "الوصف": meta.column_labels}), use_container_width=True)
    st.divider()

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "مرحباً دكتور قاسم! ارفع ملفك وسأقوم بتقديم ملخص تنفيذي فوراً 📊"}]
    if "auto_eda_done" not in st.session_state:
        st.session_state.auto_eda_done = False

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"], unsafe_allow_html=True)

    # التوليد التلقائي للرؤى (Auto-EDA) عند رفع الملف لأول مرة
    if df is not None and not st.session_state.auto_eda_done:
        st.session_state.auto_eda_done = True
        auto_prompt = f"قم بعمل ملخص تنفيذي سريع جداً (3 نقاط فقط) لأهم المتغيرات الموجودة في هذه البيانات: {list(df.columns)[:15]}... اقترح سؤالين إحصائيين قويين يمكن للمستخدم طرحهما."
        with st.chat_message("assistant"):
            with st.spinner("جاري فحص البيانات وتوليد الرؤى الافتتاحية..."):
                for key in api_keys:
                    try:
                        resp = genai.Client(api_key=key).models.generate_content(model=target_model, contents=auto_prompt)
                        st.markdown(resp.text)
                        st.session_state.messages.append({"role": "assistant", "content": resp.text})
                        break
                    except: continue

    # الدردشة التفاعلية
    if user_query := st.chat_input("✍️ اطلب تحليلاً إحصائياً، أو رسم بياني تفاعلي..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"): st.markdown(user_query)

        with st.chat_message("assistant"):
            if df is None:
                st.warning("⚠️ يرجى رفع ملف البيانات أولاً.")
            else:
                with st.spinner('جاري إجراء الاختبارات الإحصائية وبناء الرسوم التفاعلية...'):
                    meta_dict = dict(zip(meta.column_names, meta.column_labels))
                    
                    prompt = f"""
                    أنت خبير إحصاء ومبرمج علوم بيانات.
                    البيانات في `df`. الأعمدة: {list(df.columns)}. القاموس: {meta_dict}.
                    
                    التعليمات الصارمة:
                    1. 🚫 لا بيانات وهمية. استخدم `df`.
                    2. ترجم الأرقام بـ `value_labels` إن وجد: `df['var'] = df['var'].map(value_labels.get('var', {{}})).fillna(df['var'])`
                    3. ➕ في جداول crosstab، استخدم إجبارياً `margins=True, margins_name='المجموع'`.
                    4. 📊 استخدم مكتبة `px` (Plotly Express) للرسم التفاعلي واعرضه بـ `st.plotly_chart(fig, use_container_width=True)`. أزل صف المجموع قبل الرسم!
                    5. 🧪 إذا طلب المستخدم مقارنة، طبق اختبار إحصائي بـ `stats` (مثل `stats.chi2_contingency`) واطبع قيمة الـ p-value في المنصة باستخدام `st.info()`.
                    6. الكود في ```python ... ``` واستخدم `st.dataframe()` للجداول.
                    
                    طلب المستخدم: {user_query}
                    """
                    
                    response, success = None, False
                    for key in api_keys:
                        try:
                            response = genai.Client(api_key=key).models.generate_content(model=target_model, contents=prompt)
                            success = True; break
                        except: continue
                    
                    if success and response:
                        full_text = response.text
                        report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                        code_match = re.search(r"`{3}(?:python)?\s*(.*?)\s*`{3}", full_text, re.DOTALL | re.IGNORECASE)
                        
                        formatted_report = f'<div class="report-box">{report_text}</div>'
                        st.markdown(formatted_report, unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": formatted_report})
                        
                        # أزرار التصدير للتقرير
                        c1, c2 = st.columns(2)
                        with c1:
                            st.download_button("📄 تحميل التقرير (Word)", data=to_word(report_text), file_name='Report.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                        
                        if code_match:
                            st.subheader("📊 المخرجات التفاعلية:")
                            exec_env = globals().copy()
                            exec_env.update({'df': df.copy(), 'pd': pd, 'st': st, 'px': px, 'stats': stats, 'value_labels': getattr(meta, 'variable_value_labels', {})})
                            
                            try:
                                exec(code_match.group(1).strip(), exec_env)
                                for var_name, var_value in list(exec_env.items()):
                                    if isinstance(var_value, pd.DataFrame) and var_name != 'df' and not var_name.startswith('_'):
                                        with c2:
                                            st.download_button("📥 تحميل الجدول (Excel)", data=to_excel(var_value), file_name='Table.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                        break
                            except Exception as code_error:
                                st.error(f"حدث خطأ برمجي: {code_error}")
                                with st.expander("🔍 المراجعة"): st.code(code_match.group(1).strip(), language='python')
                    else:
                        st.error("❌ جميع المفاتيح استنفدت الحصة.")
else:
    st.info("👈 بانتظار تحميل المفاتيح.")
