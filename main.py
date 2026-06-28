"""
AJIO Intel - Web App (main.py)
==============================
FastAPI backend hosted on Render (free tier).
Accepts brand name → creates job in Supabase → returns job ID.
Local runner picks up job, scrapes, uploads Excel, marks done.
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import os
from datetime import datetime

app = FastAPI()

# ── Supabase config ───────────────────────────────────────────────────────────
SUPABASE_URL     = os.environ.get("SUPABASE_URL", "https://gpmeymmmppfdctqdjgrf.supabase.co")
SUPABASE_API_KEY = os.environ.get("SUPABASE_API_KEY", "sb_publishable_qQAanRfOFBczn9wtt7PZtQ_luJv_HGs")

HEADERS = {
    "apikey":        SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}

# ─────────────────────────────────────────────────────────────────────────────

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AJIO Brand Intelligence</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0f1923;
            color: #e8edf2;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        .card {
            background: #1a2535;
            border: 1px solid #2a3a50;
            border-radius: 16px;
            padding: 48px;
            width: 100%;
            max-width: 560px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }

        .logo {
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 3px;
            color: #4a9eff;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        h1 {
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
        }

        .subtitle {
            font-size: 14px;
            color: #6b7e96;
            margin-bottom: 36px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #8a9bb0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        input[type="text"] {
            width: 100%;
            padding: 14px 18px;
            background: #0f1923;
            border: 1.5px solid #2a3a50;
            border-radius: 10px;
            color: #ffffff;
            font-size: 16px;
            outline: none;
            transition: border-color 0.2s;
            margin-bottom: 20px;
        }

        input[type="text"]:focus {
            border-color: #4a9eff;
        }

        input[type="text"]::placeholder {
            color: #3a4f66;
        }

        button {
            width: 100%;
            padding: 15px;
            background: #4a9eff;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.2s, transform 0.1s;
            letter-spacing: 0.5px;
        }

        button:hover  { background: #3a8eef; }
        button:active { transform: scale(0.98); }
        button:disabled { background: #2a3a50; color: #4a5a6a; cursor: not-allowed; }

        .status-box {
            margin-top: 28px;
            padding: 20px;
            border-radius: 10px;
            font-size: 14px;
            display: none;
        }

        .status-queued  { background: #1e2d1e; border: 1px solid #2d4a2d; color: #5db85d; }
        .status-running { background: #1e2a3a; border: 1px solid #2a4060; color: #4a9eff; }
        .status-done    { background: #1a2a1a; border: 1px solid #2a5a2a; color: #5db85d; }
        .status-error   { background: #2a1a1a; border: 1px solid #5a2a2a; color: #ef5a5a; }

        .status-icon { font-size: 20px; margin-bottom: 8px; }
        .status-title { font-weight: 700; font-size: 15px; margin-bottom: 4px; }
        .status-msg { color: #6b7e96; font-size: 13px; }

        .download-btn {
            display: inline-block;
            margin-top: 14px;
            padding: 10px 24px;
            background: #2a5a2a;
            color: #5db85d;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13px;
            text-decoration: none;
            border: 1px solid #3a7a3a;
            transition: background 0.2s;
        }
        .download-btn:hover { background: #3a7a3a; }

        .spinner {
            display: inline-block;
            width: 14px; height: 14px;
            border: 2px solid #4a9eff44;
            border-top-color: #4a9eff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .footer {
            margin-top: 24px;
            font-size: 12px;
            color: #2a3a50;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">AJIO Intel</div>
        <h1>Brand Intelligence</h1>
        <p class="subtitle">Enter any brand name to scrape live data from AJIO</p>

        <label for="brand">Brand Name</label>
        <input
            type="text"
            id="brand"
            placeholder="e.g. Red Tape, Roadster, Levis"
            autocomplete="off"
        />

        <button id="scrapeBtn" onclick="submitJob()">Scrape Brand →</button>

        <div class="status-box" id="statusBox">
            <div class="status-icon" id="statusIcon"></div>
            <div class="status-title" id="statusTitle"></div>
            <div class="status-msg"  id="statusMsg"></div>
            <div id="downloadArea"></div>
        </div>
    </div>

    <div class="footer">AJIO Brand Intelligence Tool · Private Beta</div>

    <script>
        let pollInterval = null;
        let currentJobId = null;

        async function submitJob() {
            const brand = document.getElementById('brand').value.trim();
            if (!brand) {
                alert('Please enter a brand name');
                return;
            }

            const btn = document.getElementById('scrapeBtn');
            btn.disabled = true;
            btn.textContent = 'Submitting…';

            try {
                const res  = await fetch('/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body:    `brand_name=${encodeURIComponent(brand)}`
                });
                const data = await res.json();

                if (data.job_id) {
                    currentJobId = data.job_id;
                    showStatus('queued', '⏳', 'Job Queued',
                        'Your scrape job has been added to the queue. The local runner will pick it up shortly.');
                    startPolling(data.job_id);
                } else {
                    showStatus('error', '❌', 'Error', data.error || 'Unknown error');
                    btn.disabled = false;
                    btn.textContent = 'Scrape Brand →';
                }
            } catch (e) {
                showStatus('error', '❌', 'Error', e.message);
                btn.disabled = false;
                btn.textContent = 'Scrape Brand →';
            }
        }

        function startPolling(jobId) {
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(() => pollJob(jobId), 5000);
        }

        async function pollJob(jobId) {
            try {
                const res  = await fetch(`/status/${jobId}`);
                const data = await res.json();
                const status = data.status;

                if (status === 'running') {
                    showStatus('running', '<span class="spinner"></span>', 'Scraping in Progress',
                        `Scraping AJIO for "${data.brand_name}"… This takes 5–15 minutes depending on product count.`);
                } else if (status === 'done') {
                    clearInterval(pollInterval);
                    const count = data.product_count || '';
                    showStatus('done', '✅', 'Scrape Complete',
                        `${count ? count + ' products scraped. ' : ''}Your Excel file is ready.`);
                    if (data.file_url) {
                        document.getElementById('downloadArea').innerHTML =
                            `<a class="download-btn" href="${data.file_url}" target="_blank">⬇ Download Excel</a>`;
                    }
                    document.getElementById('scrapeBtn').disabled = false;
                    document.getElementById('scrapeBtn').textContent = 'Scrape Another Brand →';
                } else if (status === 'error') {
                    clearInterval(pollInterval);
                    showStatus('error', '❌', 'Scrape Failed', data.error_msg || 'An error occurred.');
                    document.getElementById('scrapeBtn').disabled = false;
                    document.getElementById('scrapeBtn').textContent = 'Try Again →';
                }
            } catch (e) {
                console.error('Poll error:', e);
            }
        }

        function showStatus(type, icon, title, msg) {
            const box = document.getElementById('statusBox');
            box.className = `status-box status-${type}`;
            box.style.display = 'block';
            document.getElementById('statusIcon').innerHTML  = icon;
            document.getElementById('statusTitle').textContent = title;
            document.getElementById('statusMsg').textContent   = msg;
        }

        // Allow Enter key to submit
        document.getElementById('brand').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') submitJob();
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse(content=HTML_PAGE, status_code=200)


@app.post("/submit")
async def submit_job(brand_name: str = Form(...)):
    """Create a new scrape job in Supabase."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/jobs",
                headers=HEADERS,
                json={
                    "brand_name": brand_name,
                    "status":     "queued",
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                job  = data[0] if isinstance(data, list) else data
                return {"job_id": job["id"], "brand_name": brand_name}
            else:
                return {"error": f"Supabase error: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Poll job status from Supabase."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/jobs",
                headers=HEADERS,
                params={"id": f"eq.{job_id}", "select": "*"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0]
                return {"error": "Job not found"}
            return {"error": f"Supabase error: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
