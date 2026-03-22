# --- 5. القائمة الجانبية (Sidebar) ---
st.sidebar.markdown("""
<div class="creator-box">
    <h3>الدكتور قاسم سمير</h3>
    <p>تصميم وتطوير المنصة</p>
    <hr style="border-color: rgba(255,255,255,0.1); margin: 10px 0;">
    <p>📧 <a href="mailto:esa.gacem@univ-blida2.dz" style="color: #6EA6FF; text-decoration: none;">esa.gacem@univ-blida2.dz</a></p>
    <p>📞 0672595801</p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🧹 تصفير جلسة التحليل"):
    st.session_state.messages = []
    st.rerun()

# --- أدوات التحكم السحابية بالمفاتيح (للمشرف) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ إدارة المحركات السحابية")

# 1. رابط الحصول على المفاتيح السريع
st.sidebar.markdown("""
<a href="https://aistudio.google.com/app/apikey" target="_blank" style="text-decoration: none;">
    <div style="background-color: rgba(15, 98, 254, 0.1); border: 1px solid #0F62FE; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; color: #6EA6FF; font-weight: bold; font-size: 0.9rem; transition: 0.3s;">
        🔗 الحصول على مفاتيح Gemini مجاناً
    </div>
</a>
""", unsafe_allow_html=True)

# 2. إضافة وفحص المفاتيح للسحابة
with st.sidebar.expander("➕ إضافة مفتاح جديد للسحابة"):
    new_key_input = st.text_input("أدخل مفتاح Gemini:", type="password")
    if st.button("فحص وحفظ"):
        if new_key_input:
            with st.spinner("جاري فحص المفتاح..."):
                is_valid, msg = verify_gemini_key(new_key_input.strip())
            
            if is_valid:
                saved, save_msg = save_key_to_cloud(new_key_input.strip())
                if saved: st.success(save_msg)
                else: st.warning(save_msg)
            else:
                st.error(msg)
        else: st.warning("الرجاء إدخال مفتاح.")
