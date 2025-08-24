# 🧩 Resume Tailor

An **AI-powered Streamlit application** that tailors your resume to any job description.  
Upload a JD and a resume template, and the app will generate **missing skills, keywords, and tailored experience bullets**—then export directly to a **DOCX resume**.

🚀 **Live Demo:** [Resume Tailor App](https://resume-tailor-eahqwrm5md2okxfjfvqcgg.streamlit.app/)

---

## ✨ Features

- 📂 Upload Job Descriptions (PDF, DOCX, TXT).
- 🧠 Powered by **OpenAI GPT (gpt-4o-mini)**.
- 🧾 Extracts **JD keywords** & identifies **missing skills**.
- 🎯 Generates **tailored, ATS-friendly bullets** for each job and project.
- 🔑 Skills organized by categories:
  - Programming
  - Data Engineering
  - Cloud
  - Database
  - ML/AI
  - Misc
- 📑 Export outputs:
  - JSON report (structured data)
  - Preset JSON (for template rendering)
  - DOCX resume using **docxtpl**

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)  
- **LLM Backend**: [OpenAI GPT-4o-mini](https://platform.openai.com/)  
- **Document Processing**: PyPDF2, python-docx  
- **Resume Generation**: docxtpl (Word template rendering)  
- **Environment Management**: python-dotenv, Streamlit Secrets  

---