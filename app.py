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
    /* تحسين شكل فقاعات الدردشة */
    .stChatMessage { border-radius: 10px; padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. وظائف معالجة البيانات والتصدير ---
@st.cache_data
def load_spss_data(file_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    df, meta = pyreadstat.read_sav(tmp_path)
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

    # زر لمسح محادثة الدردشة
    if st.button("🧹 مسح محادثة المساعد"):
        st.session_state.messages = []
        st.rerun()

# --- 4. الجزء الرئيسي من المنصة ---
st.title("📈 المنصة الذكية للتحليل الديموغرافي")
st.write("حلل قواعد بياناتك الإحصائية بلمحة بصر باستخدام قوة الذكاء الاصطناعي.")

if api_keys:
    target_model = 'gemini-2.5-flash'
    uploaded_file = st.file_uploader("📂 ارفع ملف SPSS (.sav)", type=['sav'])

    if uploaded_file:
        df, meta = load_spss_data(uploaded_file.getvalue())
        
        col1, col2, col3 = st.columns(3)
        col1.metric("عدد الحالات (Rows)", f"{df.shape[0]:,}")
        col2.metric("عدد المتغيرات (Cols)", df.shape[1])
        col3.metric("المحرك الذكي", "Gemini 2.5 Flash")

        tab1, tab2, tab3 = st.tabs(["🤖 المساعد الذكي (دردشة)", "🔍 استكشاف البيانات", "📋 دليل المتغيرات"])

        with tab2:
            st.dataframe(df.head(10), use_container_width=True)
        
        with tab3:
            meta_df = pd.DataFrame({"المتغير": meta.column_names, "الوصف": meta.column_labels})
            st.dataframe(meta_df, use_container_width=True)

        with tab1:
            # تهيئة ذاكرة المحادثة (Session State)
            if "messages" not in st.session_state:
                st.session_state.messages = [{"role": "assistant", "content": "مرحباً دكتور! أنا مساعدك الذكي. ارفع ملفك واطرح أي سؤال وسأقوم بتحليله فوراً 📊"}]

            # عرض المحادثات السابقة
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)

            # مربع الإدخال العائم للدردشة
            if user_query := st.chat_input("✍️ اسأل المساعد عن أي تحليل تريده..."):
                
                # إضافة سؤال المستخدم للدردشة وعرضه
                st.session_state.messages.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(user_query)

                # معالجة وعرض رد المساعد
                with st.chat_message("assistant"):
                    with st.spinner('جاري تحليل البيانات...'):
                        meta_dict = dict(zip(meta.column_names, meta.column_labels))
                        
                        prompt = f"""
                        أنت خبير تحليل بيانات عالمي ومبرمج Python محترف.
                        
                        البيئة الحالية:
                        - DataFrame الحقيقي موجود وجاهز للاستخدام في `df`.
                        - قائمة الأعمدة: {list(df.columns)}
                        - المتغيرات: {meta_dict}
                        
                        التعليمات الصارمة:
                        1. 🚫 لا تنشئ أي بيانات وهمية. استخدم `df` مباشرة.
                        2. ⚠️ استخدم الأعمدة الموجودة فقط.
                        3. استخدم `value_labels` لترجمة الأرقام قبل الرسم، مثال:
                           if 'var' in value_labels: df['var'] = df['var'].map(value_labels.get('var', {{}})).fillna(df['var'])
                        4. ضع كود Python داخل ```python و ```.
                        5. استخدم `st.dataframe()` و `st.bar_chart()`.
                        
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
                            # استخراج التقرير والكود
                            report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                            regex_pattern = r"`{3}(?:python)?\s*(.*?)\s*`{3}"
                            code_match = re.search(regex_pattern, full_text, re.DOTALL | re.IGNORECASE)
                            
                            # تنسيق وعرض تقرير المساعد
                            formatted_report = f'<div class="report-box">{report_text}</div>'
                            st.markdown(formatted_report, unsafe_allow_html=True)
                            
                            # حفظ التقرير في الذاكرة لتاريخ الدردشة
                            st.session_state.messages.append({"role": "assistant", "content": formatted_report})
                            
                            if code_match:
                                st.subheader("📊 المخرجات التفاعلية:")
                                exec_env = globals().copy()
                                exec_env.update({'df': df.copy(), 'pd': pd, 'st': st, 'value_labels': meta.variable_value_labels})
                                
                                try:
                                    # تنفيذ الكود وعرض الرسوم البيانية داخل فقاعة الدردشة الحالية
                                    exec(code_match.group(1).strip(), exec_env)
                                    
                                    # زر التصدير
                                    for var_name, var_value in list(exec_env.items()):
                                        if isinstance(var_value, pd.DataFrame) and var_name != 'df' and not var_name.startswith('_'):
                                            excel_data = to_excel(var_value)
                                            st.download_button("📥 تحميل الجدول الناتج (Excel)", data=excel_data, file_name='analysis_results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                            break
                                except Exception as code_error:
                                    st.error(f"خطأ برمجي: {code_error}")
                                    with st.expander("🔍 عرض الكود للمراجعة"):
                                        st.code(code_match.group(1).strip(), language='python')
                        else:
                            st.error("❌ نعتذر، جميع المفاتيح استنفدت الحصة المتاحة. يرجى تحديث الخزنة.")
else:
    st.info("👈 المنصة بانتظار تحميل المفاتيح للبدء.")
