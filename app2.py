from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PyPDF2 import PdfReader
import os

# Function to extract text from a PDF
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Function to calculate ATS Score
def calculate_ats_score(resume_text, job_description):
    documents = [resume_text, job_description]
    tfidf = TfidfVectorizer().fit_transform(documents)
    score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
    return round(score, 2)

# View to handle resume upload and ATS scoring
def upload_resume(request):
    if request.method == 'POST' and request.FILES['resume']:
        resume_file = request.FILES['resume']
        job_description = request.POST.get('job_description', '')

        fs = FileSystemStorage()
        filename = fs.save(resume_file.name, resume_file)
        uploaded_file_path = os.path.join(settings.MEDIA_ROOT, filename)

        # Extract text and calculate ATS score
        with open(uploaded_file_path, 'rb') as file:
            resume_text = extract_text_from_pdf(file)
        score = calculate_ats_score(resume_text, job_description)

        return render(request, 'ats/score_result.html', {'score': score})

    return render(request, 'ats/upload.html')

# URL Configuration
from django.urls import path

urlpatterns = [
    path('upload/', upload_resume, name='upload_resume'),
]

# Templates
# templates/ats/upload.html
upload_html = """
<h2>Upload Resume for ATS Scoring</h2>
<form method="POST" enctype="multipart/form-data">
    {% csrf_token %}
    <label for="resume">Upload Resume:</label>
    <input type="file" name="resume" required><br><br>
    <label for="job_description">Job Description:</label>
    <textarea name="job_description" rows="4" required></textarea><br><br>
    <button type="submit">Submit</button>
</form>
"""

# templates/ats/score_result.html
score_result_html = """
<h2>ATS Score Result</h2>
<p>Your ATS Score is: <strong>{{ score }}%</strong></p>
<a href="/upload/">Upload Another Resume</a>
"""

# Settings adjustments in settings.py
# Add 'ats' to INSTALLED_APPS and configure MEDIA_ROOT
INSTALLED_APPS = [
    ...,
    'ats',
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
