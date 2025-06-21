// Initialize when DOM loads
document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM fully loaded");
    try {
        fetchResumes();
        setupFormSubmit();
    } catch (error) {
        console.error("Initialization error:", error);
        showAlert("error", "Failed to initialize application");
    }
});

function setupFormSubmit() {
    const form = document.getElementById("jobForm");
    if (!form) {
        console.error("Form element not found");
        return;
    }
    
    form.addEventListener("submit", async function(event) {
        event.preventDefault();
        await handleFormSubmit(event);
    });
    console.log("Form submit handler registered");
}

async function handleFormSubmit(event) {
    const submitBtn = event.target.querySelector("button[type='submit']");
    const loadingIndicator = document.createElement('span');
    loadingIndicator.className = 'loading-indicator';
    
    try {
        // Validate form
        const formData = new FormData(event.target);
        const weights = [
            parseInt(formData.get("weight_quality") || "0"),
            parseInt(formData.get("weight_experience") || "0"),
            parseInt(formData.get("weight_years") || "0"),
            parseInt(formData.get("weight_location") || "0")
        ];
        
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        if (totalWeight !== 100) {
            throw new Error("Weights must add up to exactly 100%");
        }
        
        // UI state changes
        submitBtn.disabled = true;
        submitBtn.textContent = "Processing...";
        submitBtn.appendChild(loadingIndicator);
        
        // Clear previous errors
        clearAlerts();
        
        // Process form
        const result = await postJob(formData);
        showAlert("success", `Job posted successfully! Processed ${result.processed} resumes.`);
        
        // Refresh the resume list
        await fetchResumes();
        
    } catch (error) {
        console.error("Submission error:", error);
        showAlert("error", error.message || "Failed to process job posting");
        
    } finally {
        // Restore UI state
        submitBtn.disabled = false;
        submitBtn.textContent = "Post Job";
        if (submitBtn.contains(loadingIndicator)) {
            submitBtn.removeChild(loadingIndicator);
        }
    }
}

async function postJob(formData) {
    console.group("Form Data Being Sent");
    for (let [key, value] of formData.entries()) {
        console.log(key, key === "resumes" ? 
            `${value.name} (${value.size} bytes)` : value);
    }
    console.groupEnd();

    try {
        // Log file details for debugging
        const fileList = formData.getAll('resumes');
        console.log(`Uploading ${fileList.length} files:`);
        fileList.forEach((file, i) => {
            console.log(`File ${i+1}: ${file.name}, ${file.size} bytes, type: ${file.type}`);
        });

        // Add timeout and error handling
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch("http://127.0.0.1:8000/post-job", {
            method: "POST",
            body: formData,
            headers: {
                'Accept': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) {
            console.error("Server response not OK:", response.status, response.statusText);
            const errorText = await response.text();
            console.error("Error response body:", errorText);
            
            let errorData;
            try {
                errorData = JSON.parse(errorText);
            } catch {
                errorData = { detail: errorText || `HTTP error! Status: ${response.status}` };
            }
            
            throw new Error(errorData.detail || "Failed to post job");
        }

        const data = await response.json();
        console.log("Successful response:", data);
        return data;
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error("Request timed out");
            throw new Error("Request timed out. The server might be busy processing resumes.");
        }
        console.error("Fetch error in postJob:", error);
        throw error;
    }
}

async function fetchResumes() {
    try {
        showLoader(true);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await fetch("http://127.0.0.1:8000/get_resumes", {
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch resumes: ${response.status}`);
        }
        
        const resumes = await response.json();
        console.log("Fetched resumes:", resumes);
        renderResumes(resumes);
        
    } catch (error) {
        console.error("Fetch resumes error:", error);
        if (error.name === 'AbortError') {
            showAlert("warning", "Request timed out while fetching resumes.");
        } else {
            showAlert("warning", "Could not refresh resumes. Please try again.");
        }
    } finally {
        showLoader(false);
    }
}

function renderResumes(resumes) {
    const container = document.getElementById("resumes-container");
    if (!container) {
        console.error("Resumes container not found");
        return;
    }

    if (!resumes || resumes.length === 0) {
        container.innerHTML = `<div class="empty-state">No resumes found</div>`;
        return;
    }

    // Sort resumes by score (highest first)
    resumes.sort((a, b) => (b.score || 0) - (a.score || 0));

    container.innerHTML = resumes.map(resume => {
        // Get only first 3 lines from reason for concise display
        let shortReason = "";
        if (resume.reason) {
            const reasonLines = resume.reason.split('\n').filter(line => line.trim() !== '');
            shortReason = reasonLines.slice(0, 3).join('<br>');
            if (reasonLines.length > 3) {
                shortReason += '...';
            }
        }

        return `
        <div class="resume-card">
            <div class="resume-header">
                <h3>Resume #${resume.id?.substring(0, 8) || "Unknown"}</h3>
                ${resume.score ? `<span class="score">Score: ${resume.score.toFixed(1)}</span>` : ''}
            </div>
            <div class="resume-details">
                <p><strong>File:</strong> ${resume.filename || "Unnamed Resume"}</p>
                <p><strong>Path:</strong> ${resume.path || "N/A"}</p>
                ${resume.job_title ? `<p><strong>Applied For:</strong> ${resume.job_title}</p>` : ''}
                ${shortReason ? `<div class="reason"><strong>Analysis:</strong><br>${shortReason}</div>` : ''}
                ${resume.path ? `
                    <div class="resume-actions">
                        <a href="/download/${encodeURIComponent(resume.path)}" class="resume-link" download>Download Resume</a>
                    </div>
                ` : ''}
            </div>
        </div>
    `}).join("");
}

// Utility functions
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const header = document.querySelector('header');
    if (header) {
        header.insertAdjacentElement('afterend', alertDiv);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function clearAlerts() {
    document.querySelectorAll('.alert').forEach(alert => alert.remove());
}

function showLoader(show) {
    const loader = document.getElementById('loading-indicator') || document.createElement('div');
    loader.id = 'loading-indicator';
    loader.className = 'loader';
    loader.style.display = show ? 'block' : 'none';
    
    if (show && !document.body.contains(loader)) {
        document.body.appendChild(loader);
    }
}

// Add some basic styles dynamically
const style = document.createElement('style');
style.textContent = `
    .loading-indicator {
        display: inline-block;
        margin-left: 8px;
        width: 12px;
        height: 12px;
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .alert {
        padding: 12px;
        margin: 10px auto;
        width: 80%;
        border-radius: 4px;
        text-align: center;
    }
    
    .alert-error {
        background-color: #ffebee;
        color: #c62828;
        border: 1px solid #ef9a9a;
    }
    
    .alert-success {
        background-color: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #a5d6a7;
    }
    
    .alert-warning {
        background-color: #fff8e1;
        color: #f57f17;
        border: 1px solid #ffd54f;
    }
    
    .loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background-color: #0073e6;
        z-index: 1000;
        animation: loading 2s linear infinite;
    }
    
    @keyframes loading {
        0% { width: 0; left: 0; }
        50% { width: 100%; left: 0; }
        100% { width: 0; left: 100%; }
    }
    
    .resume-card {
        background: #fff;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 4px solid #0073e6;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .resume-card:hover {
        transform: translateY(-2px);
    }
    
    .resume-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .score {
        background: #0073e6;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
    
    .resume-details p {
        margin: 5px 0;
    }
    
    .reason {
        margin-top: 10px;
        padding: 8px;
        background: #f5f5f5;
        border-left: 3px solid #0073e6;
        max-height: 200px;
        overflow-y: auto;
    }
    
    .resume-actions {
        margin-top: 15px;
    }
    
    .resume-link {
        display: inline-block;
        color: #0073e6;
        text-decoration: none;
        padding: 5px 10px;
        border: 1px solid #0073e6;
        border-radius: 4px;
        transition: all 0.3s;
    }
    
    .resume-link:hover {
        background: #0073e6;
        color: white;
    }
    
    .empty-state {
        text-align: center;
        padding: 20px;
        color: #757575;
        font-style: italic;
    }
`;
document.head.appendChild(style);