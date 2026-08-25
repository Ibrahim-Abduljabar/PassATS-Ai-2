import streamlit as st
import os
import tempfile
import pdfplumber
from groq import Groq
import pdfkit
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
                direction: ltr;
                text-align: left;
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
        # استخدام pdfkit كبديل مستقر وآمن تماماً من الانهيارات
        pdfkit.from_string(html_template, tmp.name)
        path = tmp.name

    with open(path, "rb") as f:
        return f.read()

st.set_page_config(page_title="PassATS AI", layout="wide")
st.title("PassATS AI — ATS-Compliant Resume Optimization System")

uploaded_pdf = st.file_uploader("Upload Resume (PDF Only)", type=["pdf"])

if "job_desc_list" not in st.session_state:
    st.session_state.job_desc_list = [""]

def add_job_desc():
    st.session_state.job_desc_list.append("")

st.subheader("Job Descriptions")
for i in range(len(st.session_state.job_desc_list)):
    st.session_state.job_desc_list[i] = st.text_area(
        f"Job Description No. {i+1}",
        st.session_state.job_desc_list[i],
        height=180
    )

st.button("➕ Add Another Job Description", on_click=add_job_desc)

start = st.button("Start Resume Optimization Now")

if start:
    if not uploaded_pdf:
        st.error("Please upload a PDF file.")
    else:
        cv_text = extract_pdf_text(uploaded_pdf)
        job_descriptions = "\n\n---\n\n".join(st.session_state.job_desc_list)

        system_prompt = """
        You are a world-class expert in writing ATS-compliant resumes.

        Language Rules:
        - Write naturally and clearly in English.
        - Ensure proper grammar, phrasing, and formatting.
        - Maintain a professional, executive tone throughout.
        - Avoid mixing languages within the same sentence or section.
        - Keep the formatting consistent and clean.

        Required Structure:
        1) Personal Information
        2) Professional Summary
        3) Technical Skills
        4) Work Experience
        5) Projects
        6) Education
        7) Languages
        8) Certifications

        Formatting Rules:
        - Do NOT use HTML.
        - Do NOT use Markdown.
        - Use hyphens "-" for lists and bullet points only.
        """

        user_prompt = f"""
        Extracted Resume Content from PDF:
        {cv_text}

        Job Descriptions:
        {job_descriptions}

        Rewrite the resume entirely in English, ensuring it matches the specified structure and complies with all ATS rules.
        """

        st.info("Optimizing resume via Groq…")

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )

        final_cv_text = response.choices[0].message.content

        st.success("Optimized resume generated successfully!")
        st.subheader("Optimized Resume Output")
        st.text_area("Final CV Content", final_cv_text, height=500)

        pdf_bytes = generate_pdf_from_text(final_cv_text)

        st.download_button(
            label="Download Final PDF File",
            data=pdf_bytes,
            file_name="optimized_cv.pdf",
            mime="application/pdf"
        )
