

import os
import io
import datetime
import requests
import google.generativeai as genai
import streamlit as st
from pymongo import MongoClient
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from googlesearch import search
from fpdf import FPDF
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

genai.configure(api_key="")

# Initialize MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["resume_db"]
resumes_collection = mongo_db["resumes"]
logs_collection = mongo_db["logs"]

# Function to extract text from PDF
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

# Function to scrape job description
@st.cache_data
def scrape_requirements(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        req_lines = [p.get_text().strip() for p in paragraphs if "requirement" in p.get_text().lower()]
        return "\n".join(req_lines) if req_lines else "No specific requirements found."
    except Exception as e:
        return f"Error scraping requirements: {e}"

# Function to generate improved resume PDF
def generate_improved_pdf(original_text, improvements):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt="Original Resume:\n" + original_text)
    pdf.add_page()
    pdf.multi_cell(0, 10, txt="Improvement Suggestions Based on Job Requirements:\n" + improvements)
    
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# Function to get ATS analysis from Gemini AI
def get_gemini_response(resume_text, job_description):
    prompt = """Hey, act like a highly experienced ATS (Application Tracking System) with deep expertise in the tech industry, including software engineering, data science, data analysis, and big data engineering.

            Your primary task is to evaluate a candidate's resume against the given job description, ensuring the best possible guidance for resume optimization. The job market is highly competitive, so you must provide precise, actionable feedback to enhance the resume's ATS compatibility.

            Analyze the following resume text carefully and provide detailed improvement suggestions based on industry best practices and ATS optimization techniques.

            Evaluation Criteria:
            1. ATS Match Score – Assign a percentage score (%) indicating how well the resume aligns with the job description.  
            2. Missing Keywords – List any essential keywords or technical skills from the job description that are missing in the resume.  
            3. Section Formatting Issues – Identify any problems with headings, section names, and date formatting that may affect ATS parsing.  
            4. Job Title Match – Check if the candidate's job titles align with the job description. If not, suggest ways to incorporate them naturally.  
            5. Contact Information – Verify if the resume contains an address, email, and phone number, and highlight any missing details.  
            6. Education & Certifications – Identify whether the education section is properly structured and meets job requirements.  
            7. Hard Skills Matching – Compare listed skills in the resume with those in the job description and provide a skills alignment table.  
            8. Resume File Format – Check if the resume is ATS-compatible (e.g., PDF) and suggest improvements if necessary.  
            9. Overall Summary & Improvements – Provide a professional summary of the findings, along with personalized recommendations for enhancing ATS compliance.  

            Resume Text for Analysis:  
            {resume_text}  

            Job Description:  
            {job_description}  

            Expected JSON Response Format:  
            {  
            "ATS_Match_Score": "85%",  
            "Missing_Keywords": ["Kubernetes", "GCP", "BigQuery", "Docker"],  
            "Formatting_Issues": ["Work Experience section appears empty", "Date format should be MM/YYYY"],  
            "Job_Title_Match": "The job title 'Python Engineer' was not found in the resume. Consider adding it to the summary.",  
            "Contact_Information": {  
                "Email": "✔ Provided",  
                "Phone": "✔ Provided",  
                "Address": "❌ Not Found"  
            },  
            "Education_Match": "Education information is missing. Add relevant degrees or certifications.",  
            "Hard_Skills_Match": {  
                "Resume_Skills": ["Python", "Relational Database", "Integration Testing"],  
                "JD_Skills": ["Python", "Kubernetes", "BigQuery", "Object-Oriented Programming"],  
                "Missing_Skills": ["Kubernetes", "BigQuery"]  
            },  
            "File_Format": "Resume is in an incompatible format. Convert it to an ATS-friendly PDF.",  
            "Summary": "Your resume has strong Python skills but lacks key cloud-related technologies like Kubernetes and BigQuery. Update your job title to match the description and ensure your experience section is well-structured."  
            }  
  
            """

    
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

# Streamlit UI
st.title("📄 AI-Powered Resume Evaluator & Enhancer")
st.write("Upload your resume and provide a job description to get ATS feedback and improvement suggestions.")

# Upload Resume
uploaded_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])

# Manual Job Description Entry
job_description = st.text_area("Paste the Job Description Here")

if uploaded_file and job_description:
    resume_text = extract_pdf_text(uploaded_file)
    st.subheader("📋 Extracted Resume Text")
    st.text_area("", resume_text, height=200,label_visibility="collapsed")
    
    # Analyze Resume with AI
    if st.button("🔍 Analyze Resume"):
        st.subheader("📊 ATS Analysis & Suggestions")
        ats_feedback = get_gemini_response(resume_text, job_description)
        st.json(ats_feedback)
        
        # Save to MongoDB
        resume_doc = {"filename": uploaded_file.name, "text": resume_text, "uploaded_at": datetime.datetime.utcnow()}
        resumes_collection.insert_one(resume_doc)
    
    # Generate Improved Resume
    if st.button("📄 Download Improved Resume"):
        improved_pdf = generate_improved_pdf(resume_text, ats_feedback)
        st.download_button("📥 Download PDF", improved_pdf, file_name=f"improved_{uploaded_file.name}", mime="application/pdf")
