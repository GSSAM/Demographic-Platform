import streamlit as st
from google import genai
import pandas as pd
import pyreadstat
import tempfile
import os
import re
from io import BytesIO

# --- 1. إعدادات الواجهة المتقدمة (UI/UX) ---
st.set_page_config(page_title="منصة التحليل الديموغرافي الذكية", page_icon="📈", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, .stDataFrame {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #28a745; color: white; font-weight: bold; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#2e7bcf); color: white; }
    .report-box { background-color: #ffffff; padding: 20px; border-right: 6px solid #007bff; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .credits-box { background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-top: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.2); }
    .stChatMessage { border-radius: 10px; padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. وظائف معالجة البيانات المتعددة (الجديدة) ---
class MockMeta:
    """كائن وهمي لمحاكاة الميتا داتا الخاصة بـ SPSS عند رفع ملفات CSV أو Excel"""
    def __init__(self, columns):
        self.column_names = columns
        self.column_labels = columns  # في الإكسل، اسم العمود هو نفسه الوصف
        self.variable_value_labels = {} # لا توجد تراجم رقمية في الإكسل عادة

@st.cache_data
def load_data(file_bytes, file_name):
    file_extension = file_name.split('.')[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
        
    try:
        if file_extension == 'sav':
            df, meta = pyreadstat.read_sav(tmp_path)
        elif file_extension == 'csv':
            df = pd.read_csv(tmp_path)
            meta = MockMeta(df.columns.tolist())
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(tmp_path)
            meta = MockMeta(df.columns.tolist())
        else:
            raise ValueError("صيغة الملف غير مدعومة")
    finally:
        os.remove(tmp_path)
        
    return df, meta

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='النتائج_الإحصائية')
    return output.getvalue()

# --- 3. إدارة المفاتيح والقائمة الجانبية ---
api_keys = []

with st.sidebar:
    st.title("⚙️ حالة النظام")
    
    if "API_KEYS" in st.secrets:
        api_keys = st.secrets["API_KEYS"]
        st.success(f"✅ المنصة متصلة بالسيرفر وجاهزة للعمل.\n(تم تحميل {len(api_keys)} مفتاح)")
    else:
        st.warning("الخزنة السرية غير متوفرة. يرجى إدخال المفاتيح:")
        api_keys_input = st.text_area("مفاتيح API:", type="password", height=100)
        api_keys = [k.strip() for k in api_keys_input.replace(',', '\n').split('\n') if k.strip()]
        
    st.markdown("""
    <div class="credits-box">
        <h4>👨‍💻 تصميم وتطوير المنصة</h4>
        <h3>الدكتور قاسم سمير</h3>
        <p style="margin-bottom: 5px;">📧 <a href="mailto:esa.gacem@univ-blida2.dz" style="color: #ffdd57; text-decoration: none;">esa.gacem@univ-blida2.dz</a></p>
        <p style="margin-bottom: 0;">📞 0672595801</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🧹 مسح محادثة المساعد"):
        st.session_state.messages = [{"role": "assistant", "content": "مرحباً دكتور قاسم! أنا مساعدك الذكي. ارفع ملفك (SPSS, Excel, CSV) واطرح أي سؤال وسأقوم بتحليله فوراً 📊"}]
        st.rerun()

# --- 4. الجزء الرئيسي من المنصة (الدردشة والبيانات) ---
st.title("📈 المنصة الذكية للتحليل الديموغرافي وإدارة البيانات")

if api_keys:
    target_model = 'gemini-2.5-flash'
    
    # تعديل زر الرفع ليقبل الصيغ الجديدة
    uploaded_file = st.file_uploader("📂 ارفع قاعدة البيانات (يدعم: sav, csv, xlsx, xls)", type=['sav', 'csv', 'xlsx', 'xls'])
    
    df, meta = None, None
    if uploaded_file:
        df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("عدد الحالات (Rows)", f"{df.shape[0]:,}")
        c2.metric("عدد المتغيرات (Cols)", df.shape[1])
        c3.metric("نوع الملف", uploaded_file.name.split('.')[-1].upper())

        with st.expander("🔍 تصفح البيانات الخام ودليل المتغيرات (اضغط للفتح)", expanded=False):
            tab1, tab2 = st.tabs(["البيانات الخام", "دليل الأعمدة"])
            with tab1:
                st.dataframe(df.head(10), use_container_width=True)
            with tab2:
                # عرض الدليل بناءً على نوع الملف
                meta_df = pd.DataFrame({"اسم العمود": meta.column_names, "الوصف": meta.column_labels})
                st.dataframe(meta_df, use_container_width=True)
                
    st.divider()

    # تهيئة ذاكرة المساعد الذكي
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "مرحباً دكتور قاسم! أنا مساعدك الذكي. ارفع ملفك (SPSS, Excel, CSV) واطرح أي سؤال وسأقوم بتحليله فوراً 📊"}]

    # طباعة المحادثات السابقة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # مربع الدردشة العائم أسفل الشاشة
    if user_query := st.chat_input("✍️ اسأل المساعد عن أي تحليل تريده..."):
        
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            if df is None:
                error_msg = "⚠️ يرجى رفع ملف البيانات (sav, csv, excel) من الأعلى أولاً لأتمكن من تحليله."
                st.warning(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                with st.spinner('جاري البرمجة والتحليل بدقة...'):
                    meta_dict = dict(zip(meta.column_names, meta.column_labels))
                    
                    prompt = f"""
                    أنت خبير تحليل بيانات عالمي ومبرمج Python محترف.
                    
                    البيئة الحالية:
                    - DataFrame الحقيقي موجود وجاهز للاستخدام في المتغير `df`.
                    - قائمة الأعمدة الفعلية: {list(df.columns)}
                    - تفاصيل المتغيرات: {meta_dict}
                    
                    التعليمات الصارمة:
                    1. 🚫 لا تنشئ أي بيانات وهمية. استخدم المتغير `df` مباشرة.
                    2. ⚠️ تأكد أن الأعمدة التي ستستخدمها موجودة في قائمة الأعمدة.
                    3. إذا كان القاموس `value_labels` يحتوي على تراجم، استخدمه لترجمة الأرقام قبل الرسم:
                       if 'var_name' in value_labels and value_labels['var_name']:
                           df['var_name_label'] = df['var_name'].map(value_labels.get('var_name', {{}})).fillna(df['var_name'])
                    4. اكتب كود Python نظيف، وضع الكود بأكمله داخل علامات ```python و ```.
                    5. استخدم `st.dataframe()` للجدول و `st.bar_chart()` للرسم.
                    
                    طلب المستخدم: {user_query}
                    """
                    
                    response = None
                    success = False
                    
                    for current_key in api_keys:
                        try:
                            client = genai.Client(api_key=current_key)
                            response = client.models.generate_content(model=target_model, contents=prompt)
                            success = True
                            break
                        except Exception:
                            continue
                    
                    if success and response:
                        full_text = response.text
                        report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                        regex_pattern = r"`{3}(?:python)?\s*(.*?)\s*`{3}"
                        code_match = re.search(regex_pattern, full_text, re.DOTALL | re.IGNORECASE)
                        
                        formatted_report = f'<div class="report-box">{report_text}</div>'
                        st.markdown(formatted_report, unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": formatted_report})
                        
                        if code_match:
                            st.subheader("📊 المخرجات التفاعلية:")
                            exec_env = globals().copy()
                            exec_env.update({'df': df.copy(), 'pd': pd, 'st': st, 'value_labels': getattr(meta, 'variable_value_labels', {})})
                            
                            try:
                                exec(code_match.group(1).strip(), exec_env)
                                
                                for var_name, var_value in list(exec_env.items()):
                                    if isinstance(var_value, pd.DataFrame) and var_name != 'df' and not var_name.startswith('_'):
                                        excel_data = to_excel(var_value)
                                        st.download_button("📥 تحميل الجدول الناتج (Excel)", data=excel_data, file_name='analysis_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                        break
                            except Exception as code_error:
                                st.error(f"حدث خطأ برمجي: {code_error}")
                                with st.expander("🔍 عرض الكود للمراجعة"):
                                    st.code(code_match.group(1).strip(), language='python')
                    else:
                        st.error("❌ نعتذر، جميع المفاتيح استنفدت الحصة المتاحة (Quota).")
else:
    st.info("👈 المنصة بانتظار تحميل المفاتيح للبدء.")
