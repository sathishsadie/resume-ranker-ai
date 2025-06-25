

---

# 🧠 Resume Ranker AI

A web-based AI application that intelligently ranks resumes by analyzing how well they match job descriptions using a language model (LLM) and recruiter-defined weightages. It supports PDF/DOCX input and provides semantic, context-aware rankings using LLMs for deep reasoning.

---

## 🌐 Features

* Upload resumes and job descriptions (PDF/DOCX)
* Auto-detects resumes vs job descriptions
* Uses LLM (via OpenAI or local model) for contextual analysis
* Supports recruiter-defined weightage per skill or criteria
* Ranks resumes based on relevance to the job description
* Highlights keyword/skill matches
* Displays results in an interactive, downloadable HTML table

---

## 🛠️ Tech Stack

* **Backend**: Python, Flask (or similar)
* **AI Model**: Large Language Model (OpenAI GPT / LLM API)
* **Text Extraction**: `pdfplumber`, `python-docx`
* **Frontend**: HTML, CSS, JavaScript (`index.html`, `results.html`)
* **Utilities**: Custom scoring and weightage logic in `utils.py`

---

## 📁 Project Structure

```
resume-ranker-ai/
├── static/
│   └── js/                # JavaScript files
├── templates/
│   ├── index.html         # Upload page
│   └── results.html       # Result display page
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
└── utils.py               # Helper functions
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/sathishsadie/resume-ranker-ai.git
cd resume-ranker-ai
```

### 2. Create a Virtual Environment and Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

By default, the app will be accessible at:

```
http://127.0.0.1:5000
```

---

## 🧪 How It Works

1. **Upload**: User uploads one or more resumes and at least one job description.
2. **Text Extraction**: Resumes and JDs are parsed using `pdfplumber` (PDF) and `python-docx` (DOCX).
3. **Weightage Input**: Recruiter assigns weightage to various skills/criteria (via UI or config).
4. **LLM Analysis**:

   * Extracted text is sent to a language model prompt.
   * LLM scores each resume based on its relevance and completeness with respect to the JD and weightages.
5. **Ranking & Display**:

   * Scores are used to rank resumes.
   * Results are displayed in a sortable, searchable table with highlights.
   * Optionally, download results as a CSV.

---

## ✅ Usage Steps

1. Navigate to `http://localhost:5000`
2. Upload one or more **resumes** and at least one **job description**
3. Enter weightages for specific skills or sections (if required)
4. Click **Submit**
5. Review the **ranked results** on the next page
6. Optionally, download the report as a CSV file

---

## ⚙️ Customization

* **Switch LLM Provider**: Replace API call in `app.py` (OpenAI, Azure, Local LLM, etc.)
* **Weightage Logic**: Customize how weights are applied in `utils.py`
* **Multi-JD Support**: Extend scoring loop for comparing resumes across multiple JDs
* **Add More Metrics**: Include logic for soft skills, certifications, experience years, etc.

---

## 🧠 LLM Prompting Strategy (Under the Hood)

The LLM is prompted with:

* Parsed resume content
* Parsed JD content
* Recruiter-defined weightage per skill or section

Then asked:

* To evaluate how well the resume aligns with the JD
* To provide a normalized score (e.g., 0–100)
* To output a summary of strengths/weaknesses per resume (optional)

---



## 🙋 Contact

Maintained by [@sathishsadie](https://github.com/sathishsadie)
For feature requests or issues, please open an issue or submit a pull request on GitHub.

---
