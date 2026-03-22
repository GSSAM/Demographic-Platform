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
    .report-box { background-color: #ffffff; padding: 25px; border-right: 6px solid #007bff; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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

# --- 3. القائمة الجانبية (Sidebar) ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    api_key = st.text_input("مفتاح Google Gemini API:", type="password")
    st.divider()
    if api_key:
        st.success("تم ربط الذكاء الاصطناعي (Gemini 2.5 Flash)")
    else:
        st.warning("يرجى إدخال مفتاح الـ API")

# --- 4. الجزء الرئيسي من المنصة ---
st.title("📈 المنصة الذكية للتحليل الديموغرافي")
st.write("حلل قواعد بياناتك الإحصائية بلمحة بصر باستخدام قوة الذكاء الاصطناعي.")

if api_key:
    try:
        # استخدام المكتبة الجديدة
        client = genai.Client(api_key=api_key)
        target_model = 'gemini-2.5-flash'

        uploaded_file = st.file_uploader("📂 ارفع ملف SPSS (.sav)", type=['sav'], help="دعم كامل لملفات MICS وغيرها")

        if uploaded_file:
            df, meta = load_spss_data(uploaded_file.getvalue())
            
            col1, col2, col3 = st.columns(3)
            col1.metric("عدد الحالات (Rows)", f"{df.shape[0]:,}")
            col2.metric("عدد المتغيرات (Cols)", df.shape[1])
            col3.metric("المحرك الذكي", "Gemini 2.5 Flash")

            tab1, tab2, tab3 = st.tabs(["🔍 استكشاف البيانات", "🤖 المساعد الذكي", "📋 دليل المتغيرات"])

            with tab1:
                st.dataframe(df.head(10), use_container_width=True)
            
            with tab3:
                meta_df = pd.DataFrame({"المتغير": meta.column_names, "الوصف": meta.column_labels})
                st.dataframe(meta_df, use_container_width=True)

            with tab2:
                user_query = st.text_area("✍️ ماذا تريد أن تعرف من هذه البيانات؟", 
                                          placeholder="مثلاً: ما هو توزيع المستوى التعليمي حسب الجنس؟",
                                          height=120)
                
                if st.button("🚀 تنفيذ التحليل الذكي"):
                    if user_query:
                        with st.spinner('جاري البرمجة والتحليل بدقة...'):
                            meta_dict = dict(zip(meta.column_names, meta.column_labels))
                            
                            # التوجيه الصارم لمنع الهلوسة وإجبار الموديل على بياناتك الحقيقية
                            prompt = f"""
                            أنت خبير تحليل بيانات عالمي ومبرمج Python محترف.
                            
                            البيئة الحالية:
                            - DataFrame الحقيقي موجود وجاهز للاستخدام في المتغير `df`.
                            - قائمة الأعمدة الفعلية الموجودة في البيانات هي: {list(df.columns)}
                            - تفاصيل المتغيرات (الاسم: الوصف): {meta_dict}
                            
                            التعليمات الصارمة جداً:
                            1. 🚫 لا تنشئ أي بيانات وهمية مطلقاً. استخدم المتغير `df` الموجود مباشرة.
                            2. ⚠️ تأكد أن الأعمدة التي ستستخدمها موجودة في قائمة الأعمدة الفعلية المذكورة أعلاه.
                            3. استخدم `value_labels` لترجمة الأرقام قبل الرسم عبر دالة آمنة، مثال:
                               if 'var_name' in value_labels:
                                   df['var_name_label'] = df['var_name'].map(value_labels.get('var_name', {{}})).fillna(df['var_name'])
                            4. اكتب كود Python نظيف، وضع الكود بأكمله داخل علامات ```python و ```.
                            5. استخدم `st.dataframe()` للجدول النهائي و `st.bar_chart()` لعرض النتائج بوضوح.
                            
                            طلب المستخدم: {user_query}
                            """
                            
                            # الاستدعاء باستخدام المكتبة الأحدث
                            response = client.models.generate_content(model=target_model, contents=prompt)
                            
                            st.info("💡 رؤية المساعد واستنتاجاته:")
                            
                            # فصل النص عن الكود لعرض التقرير
                            full_text = response.text
                            report_text = re.sub(r"`{3}(?:python)?\s*(.*?)\s*`{3}", "", full_text, flags=re.DOTALL | re.IGNORECASE)
                            st.markdown(f'<div class="report-box">{report_text}</div>', unsafe_allow_html=True)
                            
                            # كتابة التعبير النمطي بأسلوب محصن ضد أخطاء السطور والنسخ (تم حل مشكلة SyntaxError)
                            regex_pattern = r"`{3}(?:python)?\s*(.*?)\s*`{3}"
                            code_match = re.search(regex_pattern, full_text, re.DOTALL | re.IGNORECASE)
                            
                            if code_match:
                                st.subheader("📊 المخرجات التفاعلية:")
                                
                                # الدمج الذكي لبيئة التنفيذ لمنع خطأ اختفاء المتغيرات (تم حل مشكلة Scope Error)
                                exec_env = globals().copy()
                                exec_env.update({
                                    'df': df.copy(), 
                                    'pd': pd, 
                                    'st': st, 
                                    'value_labels': meta.variable_value_labels
                                })
                                
                                try:
                                    exec(code_match.group(1).strip(), exec_env)
                                    
                                    # محرك استخراج الجداول لزر التحميل Excel
                                    for var_name, var_value in list(exec_env.items()):
                                        if isinstance(var_value, pd.DataFrame) and var_name != 'df' and not var_name.startswith('_'):
                                            st.divider()
                                            excel_data = to_excel(var_value)
                                            st.download_button(
                                                label="📥 تحميل الجدول الناتج (Excel)",
                                                data=excel_data,
                                                file_name='analysis_results.xlsx',
                                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                                            )
                                            break # زر تحميل لجدول واحد يكفي لتجنب التكرار
                                            
                                except Exception as code_error:
                                    st.error(f"حدث خطأ برمجي أثناء تحليل بياناتك: {code_error}")
                                    with st.expander("🔍 عرض الكود الذي تسبب في الخطأ لمراجعته"):
                                        st.code(code_match.group(1).strip(), language='python')
                            else:
                                st.warning("لم يقم المساعد بتوليد كود قابل للتنفيذ هذه المرة. يرجى إعادة صياغة السؤال.")
                    else:
                        st.warning("يرجى كتابة سؤال أولاً.")
    except Exception as e:
        st.error(f"حدث خطأ في النظام: {e}")
else:
    st.info("👈 ابدأ بإدخال مفتاح API في القائمة الجانبية.")