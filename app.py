import os
import shutil
import uuid
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json
from fastapi import FastAPI, Form, File, UploadFile, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import fitz  # PyMuPDF
from dotenv import load_dotenv
from pydantic import BaseModel, conint
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import re
# Enhanced configuration
class Config:
    UPLOAD_DIR = Path("uploads")
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".pdf"}
    DATABASE_FILE = Path("resumes_db.json")  # Changed to Path object

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recruiter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI with better metadata
app = FastAPI(
    title="Recr+uiter Dashboard API",
    version="1.1.0",
    description="API for automated resume scoring and job matching",
    contact={
        "name": "Support",
        "email": "support@recruiter.com"
    },
    license_info={
        "name": "MIT",
    },
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Make sure POST is included
    allow_headers=["*"],
)

# Static and template files with cache control
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize upload directory
Config.UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

# Check if upload directory is writable
if not os.access(Config.UPLOAD_DIR, os.W_OK):
    logger.critical(f"Upload directory {Config.UPLOAD_DIR} is not writable!")
    raise PermissionError(f"Upload directory {Config.UPLOAD_DIR} is not writable!")

# Database setup
class ResumeDB:
    @staticmethod
    def load() -> Dict[str, Any]:
        try:
            if Config.DATABASE_FILE.exists():
                with open(Config.DATABASE_FILE, "r") as f:
                    return json.load(f)
            return {"resumes": []}  # Initialize with empty structure
        except Exception as e:
            logger.error(f"Database load failed: {e}")
            return {"resumes": []}  # Fallback empty structure

    @staticmethod
    def save(data: Dict[str, Any]):
        try:
            with open(Config.DATABASE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            raise

# Pydantic models for request/response validation
class WeightInput(BaseModel):
    quality: conint(ge=0, le=100)
    experience: conint(ge=0, le=100)
    years: conint(ge=0, le=100)
    location: conint(ge=0, le=100)

class ResumeResponse(BaseModel):
    filename: str
    score: float
    reason: str
    path: str
    status: str
    processed_at: str

# Initialize LLM with retry logic
def initialize_llm():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempting to initialize LLM (attempt {attempt+1})")
            llm = ChatOllama(
                model="deepseek-r1:1.5b",
                temperature=0,
                timeout=30
            )
            # Test connection with simpler prompt
            response = llm([HumanMessage(content="Say 'LLM is working'")])
            print(f"LLM test response: {response.content}")
            logger.info("LLM initialized successfully")
            return llm
        except Exception as e:
            logger.warning(f"LLM initialization attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached for LLM initialization")
                print("CRITICAL: Could not initialize LLM. Is Ollama running with the deepseek-r1:1.5b model?")
                return None  # Return None instead of raising, to allow graceful degradation
            import time
            time.sleep(2)  # Wait before retrying

llm = initialize_llm()

# Enhanced routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main recruiter dashboard page"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return HTMLResponse(content="Error loading dashboard. Please check server logs.")

@app.post("/post-job", response_model=Dict[str, Any])
async def post_job(
    job_title: str = Form(..., min_length=3, max_length=100),
    description: str = Form(..., min_length=10),
    years_needed: str = Form(...),
    weight_quality: int = Form(..., ge=0, le=100),
    weight_experience: int = Form(..., ge=0, le=100),
    weight_years: int = Form(..., ge=0, le=100),
    weight_location: int = Form(..., ge=0, le=100),
    resumes: List[UploadFile] = File(...)
):
    """
    Process job posting and score uploaded resumes with enhanced validation and error handling
    """
    # Check if LLM is available
    if llm is None:
        logger.error("LLM not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable. Please try again later."
        )
    
    # Validate weights
    weights = WeightInput(
        quality=weight_quality,
        experience=weight_experience,
        years=weight_years,
        location=weight_location
    )
    
    if sum(weights.dict().values()) != 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Weights must sum to 100%"
        )
    
    resume_results = []
    db = ResumeDB.load()
    if "resumes" not in db:
        db["resumes"] = []
    
    for resume in resumes:
        try:
            # Log file details for debugging
            logger.info(f"Received file: {resume.filename}, size: {resume.size}")
            
            # Validate file
            if not resume.filename.lower().endswith('.pdf'):
                logger.warning(f"Skipped non-PDF file: {resume.filename}")
                resume_results.append({
                    "filename": resume.filename,
                    "error": "Only PDF files are supported",
                    "status": "failed",
                    "processed_at": datetime.now().isoformat()
                })
                continue
                
            if resume.size > Config.MAX_FILE_SIZE:
                raise ValueError("File size exceeds 10MB limit")
            
            # Secure file handling
            unique_filename = f"{uuid.uuid4()}_{Path(resume.filename).name}"
            file_path = Config.UPLOAD_DIR / unique_filename
            
            logger.info(f"Processing resume: {resume.filename}")
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(resume.file, buffer)
            
            # Extract and validate text
            text = extract_text_from_pdf(file_path)
            if not text.strip():
                raise ValueError("Empty resume content")
            
            # Process with LLM
            prompt = generate_prompt(
                job_title, description, years_needed,
                weights.quality, weights.experience,
                weights.years, weights.location,
                text
            )
            response = llm([HumanMessage(content=prompt)])
            content = response.content
            
            # Extract score
            score = extract_score(content)
            
            # Extract a concise reason (first 3 lines)
            reason = extract_concise_reason(content)
            
            # Prepare result - only include the required fields
            result = {
                "id": str(uuid.uuid4()),
                "job_title": job_title,
                "filename": resume.filename,
                "score": score,
                "reason": reason,  # Concise reason instead of full content
                "path": str(file_path),
                "content":content,
                "status": "processed",
                "processed_at": datetime.now().isoformat()
            }
            
            # Store in database
            db["resumes"].append(result)
            resume_results.append(result)
            
        except Exception as e:
            error_msg = f"Error processing {resume.filename}: {str(e)}"
            logger.error(error_msg)
            resume_results.append({
                "filename": resume.filename,
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.now().isoformat()
            })
    
    # Save database
    ResumeDB.save(db)
    
    # Return sorted results
    successful_results = sorted(
        [r for r in resume_results if r.get("status") == "processed"],
        key=lambda x: x["score"],
        reverse=True
    )
    
    return JSONResponse(
        content=jsonable_encoder({
            "job_title": job_title,
            "total_resumes": len(resumes),
            "processed": len(successful_results),
            "failed": len(resumes) - len(successful_results),
            "results": successful_results
        }),
        headers={"X-Total-Count": str(len(successful_results))}
    )

@app.get("/get_resumes", response_model=List[Dict[str, Any]])
async def get_resumes(limit: int = 10, skip: int = 0):
    """
    Retrieve processed resumes with pagination and caching headers
    """
    try:
        db = ResumeDB.load()
        results = db.get("resumes", [])[skip:skip+limit]
        
        # Filter out personal information fields from the response
        filtered_results = []
        for resume in results:
            # Remove personal info fields if they exist
            filtered_resume = {k: v for k, v in resume.items() if k not in ['name', 'email', 'location', 'years_exp']}
            filtered_results.append(filtered_resume)
        
        return JSONResponse(
            content=jsonable_encoder(filtered_results),
            headers={
                "X-Total-Count": str(len(db.get("resumes", []))),
                "Cache-Control": "public, max-age=60"
            }
        )
    except Exception as e:
        logger.error(f"Failed to fetch resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes"
        )

# Utility functions with enhanced features
def extract_text_from_pdf(path: Path) -> str:
    """Extract and validate text from PDF with improved error handling"""
    try:
        text = ""
        with fitz.open(path) as doc:
            if doc.is_encrypted:
                doc.authenticate("")  # Try empty password
            for page in doc:
                text += page.get_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise ValueError(f"Could not extract text: {e}")

def generate_prompt(
    job_title: str,
    description: str,
    years_needed: str,
    w1: int, w2: int, w3: int, w4: int,
    resume_text: str
) -> str:
    """Generate structured prompt with improved formatting"""
    return f"""
You are a resume evaluator. Based on the following job posting and criteria, give a structured evaluation of the resume. Your response MUST include a score from 0 to 100 and follow the format exactly.

**Job Title:** {job_title}
**Job Description:** {description}
**Required Years of Experience:** {years_needed}

**Evaluation Weights:**
- CV Quality: {w1}%
- Relevant Experience: {w2}%
- Years of Experience: {w3}%
- Location Compatibility: {w4}%

**Candidate Resume:**
{resume_text[:15000]}

**RESPONSE FORMAT (DO NOT SKIP ANY PART):**
Score: [0.0-100.0]
Reason: [Concise summary in 3-5 lines]
Strengths:
- Bullet point 1
- Bullet point 2
Weaknesses:
- Bullet point 1
- Bullet point 2
Recommendation: [Short recommendation]
"""

import re

def extract_score(llm_response: str) -> int:
    match = re.search(r"\*\*Score:\*\*\s*(\d+)", llm_response)
    match1 = re.search(r"\*\*Score\t:\*\*\s*(\d+)", llm_response)
    # match2 = re.search(r"\*\*Score :\*\*\s*(\d+)", llm_response)
    if match:
        return float(match.group(1))
    if match1:
        return float(match1.group(1))
    return 0.0  # or raise an error if score is mandatory


def extract_concise_reason(response_text: str) -> str:
    """Extract a concise reason (first 3 meaningful lines) from the LLM response"""
    try:
        import re
        
        # Try to find the "Reason:" section first
        reason_match = re.search(r"Reason:\s*(.*?)(?=\n\s*(?:Strengths:|Weaknesses:|Recommendation:|$))", 
                               response_text, re.DOTALL | re.IGNORECASE)
        
        if reason_match:
            reason_text = reason_match.group(1).strip()
        else:
            # If no explicit reason section, get content after "Score:" but before other sections
            score_match = re.search(r"Score:.*?\n(.*?)(?=\n\s*(?:Strengths:|Weaknesses:|Recommendation:|$))", 
                                  response_text, re.DOTALL | re.IGNORECASE)
            if score_match:
                reason_text = score_match.group(1).strip()
            else:
                # Last resort: just get first paragraph after any line containing "Score"
                lines = response_text.split('\n')
                reason_text = ""
                found_score = False
                for line in lines:
                    if "score" in line.lower():
                        found_score = True
                        continue
                    if found_score and line.strip():
                        reason_text = line.strip()
                        break
        
        # Get first 3 meaningful lines
        meaningful_lines = [line.strip() for line in reason_text.split('\n') if line.strip()]
        result = '\n'.join(meaningful_lines[:3])
        
        return result if result else "No reason provided"
        
    except Exception as e:
        logger.warning(f"Reason extraction error: {e}")
        return "Error extracting reason"
@app.get("/download/{filename:path}")
async def download_file(filename: str):
    """Serve a file for download"""
    try:
        return FileResponse(
            path=filename, 
            filename=Path(filename).name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=404, detail="File not found")
# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Debug endpoint for testing
@app.get("/debug/test-upload", response_class=HTMLResponse)
async def test_upload():
    """Simple form for testing upload functionality"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Upload</title>
    </head>
    <body>
        <h1>Test File Upload</h1>
        <form action="/post-job" method="post" enctype="multipart/form-data">
            <input type="text" name="job_title" value="Test Job"><br>
            <textarea name="description">Test description</textarea><br>
            <input type="text" name="years_needed" value="2"><br>
            <input type="number" name="weight_quality" value="25"><br>
            <input type="number" name="weight_experience" value="25"><br>
            <input type="number" name="weight_years" value="25"><br>
            <input type="number" name="weight_location" value="25"><br>
            <input type="file" name="resumes" multiple><br>
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """
@app.on_event("startup")
async def reset_database_on_startup():
    try:
        logger.info("Resetting resumes_db.json on startup...")
        ResumeDB.save({"resumes": []})
        logger.info("resumes_db.json has been cleared.")
    except Exception as e:
        logger.error(f"Failed to reset database on startup: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=2
    )