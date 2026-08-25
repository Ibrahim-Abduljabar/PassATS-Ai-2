import streamlit as st
import os
import tempfile
import pdfplumber
from groq import Groq
from weasyprint import HTML
from logsnag import LogSnag

log_client = LogSnag(token=st.secrets["LOGSNAG_TOKEN"], project="passats-ai")
log_client.track(channel="visits", event="New Visit")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() or "" for page in pdf.pages])

def generate_pdf_from_text(text_content):
    html_template = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                direction: rtl;
                text-align: right;
                line-height: 1.8;
                font-size: 16px;
                padding: 30px;
            }}
        </style>
    </head>
    <body>
        <pre style="white-space: pre-wrap;">{text_content}</pre>
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        HTML(string=html_template).write_pdf(tmp.name)
        path = tmp.name

    with open(path, "rb") as f:
        return f.read()

st.set_page_config(page_title="PassATS AI", layout="wide")
st.title("PassATS AI — نظام تحسين السيرة الذاتية المتوافق مع ATS")

uploaded_pdf = st.file_uploader("ارفع السيرة الذاتية (PDF فقط)", type=["pdf"])

if "job_desc_list" not in st.session_state:
    st.session_state.job_desc_list = [""]

def add_job_desc():
    st.session_state.job_desc_list.append("")

st.subheader("الأوصاف الوظيفية")
for i in range(len(st.session_state.job_desc_list)):
    st.session_state.job_desc_list[i] = st.text_area(
        f"الوصف الوظيفي رقم {i+1}",
        st.session_state.job_desc_list[i],
        height=180
    )

st.button("➕ أضف وصف وظيفي آخر", on_click=add_job_desc)

start = st.button("ابدأ تحسين السيرة الذاتية الآن")

if start:
    if not uploaded_pdf:
        st.error("الرجاء رفع ملف PDF.")
    else:
        cv_text = extract_pdf_text(uploaded_pdf)
        job_descriptions = "\n\n---\n\n".join(st.session_state.job_desc_list)

        system_prompt = """
        أنت خبير عالمي في كتابة السير الذاتية المتوافقة مع ATS.

        قواعد اللغة:
        - اكتب العربي بشكل طبيعي وواضح بدون أي تكسير أو انعكاس.
        - اكتب العربي من اليمين إلى اليسار بشكل صحيح.
        - إذا كان القسم إنجليزي، اكتبه إنجليزي طبيعي.
        - ممنوع دمج لغتين داخل نفس الجملة.
        - إذا وجدت كلمات عربية وإنجليزية متجاورة، افصلها إلى سطرين.
        - ممنوع الترجمة إلا إذا كان النص الأصلي غير مفهوم.
        - حافظ على اللغة الأصلية لكل قسم كما جاءت.

        الهيكل المطلوب:
        1) المعلومات الشخصية
        2) الملخص المهني
        3) المهارات التقنية
        4) الخبرات العملية
        5) المشاريع
        6) التعليم
        7) اللغات
        8) الشهادات

        قواعد التنسيق:
        - لا تستخدم HTML.
        - لا تستخدم Markdown.
        - استخدم الشرطات "-" للقوائم فقط.
        """

        user_prompt = f"""
        السيرة الذاتية المستخرجة من PDF:
        {cv_text}

        الأوصاف الوظيفية:
        {job_descriptions}

        أعد كتابة السيرة الذاتية مع الحفاظ على اللغة الأصلية لكل قسم.
        """

        st.info("جاري تحسين السيرة الذاتية عبر Groq…")

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )

        final_cv_text = response.choices[0].message.content

        st.success("تم إنشاء السيرة الذاتية المحسّنة!")
        st.subheader("السيرة الذاتية بعد التحسين")
        st.text_area("CV النهائي", final_cv_text, height=500)

        pdf_bytes = generate_pdf_from_text(final_cv_text)

        st.download_button(
            label="تحميل ملف PDF النهائي",
            data=pdf_bytes,
            file_name="optimized_cv.pdf",
            mime="application/pdf"
        )
 
