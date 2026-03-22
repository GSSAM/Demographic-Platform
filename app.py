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

st.set_page_config(page_title="SPSS Analytics Pro", page_icon="📊", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
:root{--spss-blue:#0F62FE;--spss-dark:#161616;--spss-light:#F4F4F4;--spss-border:#E0E0E0;}
*{font-family:'Cairo',sans-serif;}
.stApp{background:linear-gradient(135deg,#1e3c72 0%,#2a5298 100%);}
.main .block-container{background:white;padding:2rem;border-radius:15px;box-shadow:0 10px 40px rgba(0,0,0,0.2);}
.stButton>button{background:linear-gradient(90deg,#0F62FE 0%,#0353E9 100%);color:white;font-weight:600;border:none;border-radius:8px;padding:0.6rem 1.5rem;transition:all 0.3s ease;box-shadow:0 4px 12px rgba(15,98,254,0.3);}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(15,98,254,0.4);}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#161616 0%,#262626 100%);}
[data-testid="stSidebar"] *{color:white !important;}
.report-box{background:linear-gradient(135deg,#f5f7fa 0%,#e4e8ed 100%);padding:1.5rem;border-radius:12px;border-right:6px solid #0F62FE;box-shadow:0 8px 24px rgba(0,0,0,0.1);margin:1rem 0;direction:rtl;text-align:right;line-height:1.8;}
[data-testid="stMetricValue"]{font-size:1.8rem;font-weight:700;color:#0F62FE;}
.status-badge{display:inline-block;padding:0.3rem 0.8rem;border-radius:20px;font-size:0.85rem;font-weight:600;}
.status-success{background:#24A148;color:white;}
</style>""", unsafe_allow_html=True)


class MockMeta:
    def __init__(self, columns):
        self.column_names = columns
        self.column_labels = columns
        self.variable_value_labels = {}


@st.cache_data
def load_data(file_bytes, file_name):
    ext = file_name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
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


def get_api_keys():
    if "API_KEYS" not in st.secrets:
        st.error("لم يتم العثور على مفاتيح API")
        return []
    return list(st.secrets["API_KEYS"])


async def call_gemini(prompt):
    keys = get_api_keys()
    if not keys:
        return None
    random.shuffle(keys)
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(model="gemini-2.0-flash-exp", contents=prompt)
            return response
        except Exception:
            continue
    return None


def safe_exec(code, df):
    env = {'df': df.copy(), 'pd': pd, 'np': np, 'st': st, 'px': px, 'go': go, 'stats': stats}
    try:
        exec(code, env)
        return True, None
    except Exception as e:
        return False, str(e)


def make_prompt(query, cols, shape, dtypes):
    p = (
        "أنت محلل إحصائي خبير متخصص في SPSS وتحليل البيانات.\n"
        "مهمتك تنفيذ التحليلات المطلوبة بدقة عالية وبدون أي هلوسة.\n\n"
        "البيانات المتاحة:\n"
        "- الأعمدة: " + str(cols) + "\n"
        "- عدد السجلات: " + str(shape[0]) + "\n"
        "- عدد المتغيرات: " + str(shape[1]) + "\n"
        "- أنواع البيانات: " + str(dtypes) + "\n\n"
        "تعليمات صارمة:\n"
        "1. اكتب كود Python قابل للتنفيذ داخل ```python و ```\n"
        "2. المتغيرات المتاحة: df, pd, np, st, px, go, stats\n"
        "3. استخدم st.write() أو st.dataframe() أو st.metric() لعرض النتائج\n"
        "4. استخدم st.plotly_chart(fig, use_container_width=True) للرسوم\n"
        "5. لا تستخدم print() أو matplotlib أو seaborn أو plt\n"
        "6. تأكد أن أسماء الأعمدة مطابقة تماماً للقائمة أعلاه\n"
        "7. أضف margins=True و margins_name='المجموع' في جداول التقاطع\n"
        "8. في الاختبارات الإحصائية اعرض P-value واتخذ القرار\n\n"
        "أمثلة صحيحة:\n\n"
        "إحصاء وصفي:\n"
        "```python\n"
        "desc = df.describe()\n"
        "st.dataframe(desc)\n"
        "```\n\n"
        "جدول تكرار:\n"
        "```python\n"
        "freq = df['col'].value_counts().reset_index()\n"
        "freq.columns = ['القيمة', 'التكرار']\n"
        "freq['النسبة'] = (freq['التكرار'] / freq['التكرار'].sum() * 100).round(2)\n"
        "st.dataframe(freq)\n"
        "```\n\n"
        "جدول تقاطعي:\n"
        "```python\n"
        "cross = pd.crosstab(df['var1'], df['var2'], margins=True, margins_name='المجموع')\n"
        "st.dataframe(cross)\n"
        "```\n\n"
        "رسم أعمدة:\n"
        "```python\n"
        "data = df['col'].value_counts().reset_index()\n"
        "data.columns = ['الفئة', 'العدد']\n"
        "fig = px.bar(data, x='الفئة', y='العدد', title='التوزيع')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "رسم دائري:\n"
        "```python\n"
        "fig = px.pie(df, names='col', title='التوزيع')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "رسم صندوقي:\n"
        "```python\n"
        "fig = px.box(df, y='col', title='العنوان')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "هيستوجرام:\n"
        "```python\n"
        "fig = px.histogram(df, x='col', nbins=20, title='التوزيع')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "رسم مبعثر:\n"
        "```python\n"
        "fig = px.scatter(df, x='var1', y='var2', title='العلاقة')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "اختبار t:\n"
        "```python\n"
        "g1 = df[df['group']=='A']['val'].dropna()\n"
        "g2 = df[df['group']=='B']['val'].dropna()\n"
        "t, p = stats.ttest_ind(g1, g2)\n"
        "st.write('t =', round(t, 4))\n"
        "st.write('P-value =', round(p, 4))\n"
        "if p < 0.05:\n"
        "    st.success('دالة إحصائياً')\n"
        "else:\n"
        "    st.info('غير دالة إحصائياً')\n"
        "```\n\n"
        "كاي تربيع:\n"
        "```python\n"
        "ct = pd.crosstab(df['v1'], df['v2'])\n"
        "chi2, p, dof, exp = stats.chi2_contingency(ct)\n"
        "st.write('كاي تربيع =', round(chi2, 4))\n"
        "st.write('P-value =', round(p, 4))\n"
        "st.write('درجات الحرية =', dof)\n"
        "```\n\n"
        "مصفوفة الارتباط:\n"
        "```python\n"
        "num_cols = df.select_dtypes(include='number').columns.tolist()\n"
        "corr = df[num_cols].corr()\n"
        "st.dataframe(corr)\n"
        "fig = px.imshow(corr, text_auto=True, title='مصفوفة الارتباط')\n"
        "st.plotly_chart(fig, use_container_width=True)\n"
        "```\n\n"
        "السؤال: " + query + "\n\n"
        "أجب بتفسير مختصر بالعربية ثم الكود القابل للتنفيذ ثم تفسير النتائج."
    )
    return p


st.sidebar.markdown("""<div style="text-align:center;padding:1.5rem;">
<h1 style="color:#0F62FE;font-size:2.5rem;margin:0;">📊</h1>
<h2 style="margin:0.5rem 0;font-size:1.3rem;">SPSS Analytics Pro</h2>
<div style="height:3px;background:linear-gradient(90deg,#0F62FE,#0353E9);margin:1rem 0;"></div>
</div>""", unsafe_allow_html=True)

st.sidebar.markdown("""<div style="background:rgba(255,255,255,0.1);padding:1rem;border-radius:10px;margin:1rem 0;">
<h4 style="color:#0F62FE;margin:0;">👨‍🏫 أ. قاسم سمير</h4>
<p style="margin:0.3rem 0;font-size:0.85rem;">📊 إحصاء وتحليل ديموغرافي</p>
<p style="margin:0.3rem 0;font-size:0.85rem;">📱 0672595801</p>
</div>""", unsafe_allow_html=True)

if st.sidebar.button("🧹 مسح الذاكرة", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""<div style="padding:0.8rem;background:rgba(255,255,255,0.05);border-radius:8px;font-size:0.8rem;">
<strong style="color:#0F62FE;">📌 الإمكانيات:</strong><br/>
• التحليل الوصفي الشامل<br/>
• الاختبارات الإحصائية<br/>
• الرسوم التفاعلية Plotly<br/>
• جداول التكرار والتقاطع<br/>
• تحليل الارتباط والانحدار<br/>
• اختبار الفرضيات
</div>""", unsafe_allow_html=True)

st.markdown("""<div style="text-align:center;padding:1.5rem 0;">
<h1 style="font-size:2.2rem;margin:0;color:#0F62FE;">🔬 المختبر الإحصائي الذكي</h1>
<p style="color:#666;font-size:1rem;margin-top:0.5rem;">تحليل بيانات متقدم بالذكاء الاصطناعي</p>
</div>""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 ارفع ملف البيانات", type=['sav', 'csv', 'xlsx'], help="يدعم SPSS و Excel و CSV")

if uploaded_file:
    df, meta = load_data(uploaded_file.getvalue(), uploaded_file.name)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 الحالات", str(df.shape[0]))
    c2.metric("📊 المتغيرات", str(df.shape[1]))
    c3.metric("🔢 القيم الناقصة", str(df.isnull().sum().sum()))
    with c4:
        st.markdown('<div style="padding-top:10px;"><span class="status-badge status-success">✅ متصل</span></div>', unsafe_allow_html=True)
    with st.expander("👁️ معاينة البيانات", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)
    with st.expander("📋 معلومات المتغيرات", expanded=False):
        vi = pd.DataFrame({'المتغير': df.columns, 'النوع': df.dtypes.astype(str), 'القيم الفريدة': [df[c].nunique() for c in df.columns], 'الناقصة': [df[c].isnull().sum() for c in df.columns]})
        st.dataframe(vi, use_container_width=True)
    st.markdown("---")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        av = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=av):
            st.markdown(msg["content"], unsafe_allow_html=True)
    user_query = st.chat_input("✍️ اكتب طلبك هنا...")
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🔄 جاري التحليل والتنفيذ..."):
                dt = {}
                for col in df.columns:
                    dt[col] = str(df[col].dtype)
                prompt = make_prompt(user_query, list(df.columns), df.shape, dt)
                response = asyncio.run(call_gemini(prompt))
                if response:
                    full_text = response.text
                    code_pattern = r"```python\s*\n(.*?)```"
                    code_matches = re.findall(code_pattern, full_text, re.DOTALL)
                    report_text = re.sub(code_pattern, "", full_text, flags=re.DOTALL).strip()
                    if report_text:
                        st.markdown('<div class="report-box">' + report_text + '</div>', unsafe_allow_html=True)
                    if code_matches:
                        for i, code in enumerate(code_matches):
                            code = code.strip()
                            if code:
                                with st.expander("📝 الكود " + str(i + 1), expanded=False):
                                    st.code(code, language='python')
                                ok, err = safe_exec(code, df)
                                if not ok:
                                    st.error("❌ خطأ: " + err)
                                    st.info("💡 تحقق من أسماء المتغيرات وأعد الصياغة")
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                else:
                    st.error("❌ فشل الاتصال. حاول مرة أخرى.")
                    st.session_state.messages.append({"role": "assistant", "content": "فشل الاتصال"})
else:
    st.markdown("""<div style="text-align:center;padding:2rem;background:#f8f9fa;border-radius:15px;margin:1rem 0;">
    <h2 style="color:#0F62FE;">👋 مرحباً بك في المختبر الإحصائي الذكي</h2>
    <p style="color:#666;font-size:1.1rem;">ارفع ملف البيانات للبدء في التحليل</p>
    <div style="margin-top:1.5rem;text-align:right;max-width:500px;margin-left:auto;margin-right:auto;">
    <p style="color:#0F62FE;font-weight:600;">💡 أمثلة:</p>
    <ul style="color:#666;line-height:2.2;list-style:none;padding:0;">
    <li>• احسب المتوسط الحسابي والانحراف المعياري</li>
    <li>• ارسم رسماً دائرياً لتوزيع الجنس</li>
    <li>• اعرض جدول تكرار للمستوى التعليمي</li>
    <li>• أجرِ اختبار t للفرق بين مجموعتين</li>
    <li>• احسب معامل الارتباط بين متغيرين</li>
    <li>• ارسم مخطط صندوقي للمقارنة</li>
    </ul></div></div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""<div style="text-align:center;color:#666;font-size:0.85rem;">
<strong>SPSS Analytics Pro</strong> | Powered by Gemini AI | تطوير: <strong>أ. قاسم سمير</strong> | 📱 0672595801
</div>""", unsafe_allow_html=True)
