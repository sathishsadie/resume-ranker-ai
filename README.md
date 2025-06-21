# 🧠 Resume Ranker AI

A web-based AI application that intelligently ranks resumes based on how well they match one or more job descriptions using NLP and embedding similarity. The system includes both a Python backend and a responsive frontend using HTML/CSS/JavaScript.

---

## 🌐 Features

- Upload resumes and job descriptions (PDF/DOCX)
- Intelligent JD vs Resume detection
- Ranks resumes by semantic similarity using embeddings
- Highlights keyword matches
- Displays results in a user-friendly HTML table
- Downloadable ranked results

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask (or similar)
- **NLP**: Sentence-Transformers (SBERT), Scikit-learn
- **Frontend**: HTML, CSS, JavaScript (`index.html`, `results.html`)
- **Parsing**: pdfplumber, python-docx

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

````

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/sathishsadie/resume-ranker-ai.git
cd resume-ranker-ai
````

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

This will start the app locally. By default, it's accessible at:

```
http://127.0.0.1:5000
```

---

## 🧪 How It Works

1. Upload resumes and job descriptions (PDF/DOCX)
2. App extracts text using `pdfplumber` and `python-docx`
3. Embeddings are generated using `sentence-transformers`
4. Cosine similarity is computed between each resume and the JD(s)
5. The backend sends data to `results.html` to display rankings
6. Users can view/download sorted results

---

## ✅ Usage Steps

1. Open `http://localhost:5000`
2. Upload **at least one job description** and **one or more resumes**
3. Click "Submit"
4. View ranked resumes on the results page
5. Optionally download a CSV of the results

---

## 🧩 Customization

* **Change similarity model**: Modify model in `app.py`
* **Extend to multiple JDs**: Adjust logic for comparison
* **Add filters/keywords**: Update `results.html` or `utils.py`

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for more details.

---

## 🙋 Contact

Maintained by [@sathishsadie](https://github.com/sathishsadie).
For issues or contributions, open a GitHub issue or pull request.
