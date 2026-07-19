# ScreenSmart - AI Resume Screening & Recruiter Suite

ScreenSmart is a high-fidelity, production-ready AI Resume Screening System built for hackathon evaluation. It automates parsing, analyzing, scoring, and proposing interview slots for batches of candidates, presenting all insights in a recruiter-friendly dashboard.

## Folder Structure & Phase Completions

Based on the structure, here is a status breakdown of each component and what has been successfully completed:

```
ScreenSmart/
├── backend/
│   ├── app.py                 # [COMPLETED] Core Flask routes, local candidate database, sample loader
│   ├── parser.py              # [COMPLETED] Text extractor from PDF using PyMuPDF (fitz)
│   ├── gemini_service.py      # [COMPLETED] ATS scoring model using Gemini-3.5-Flash returning structured JSON
│   └── templates/
│       ├── about.html         # [COMPLETED] Premium landing page resembling Resume Gyani
│       ├── index.html         # [COMPLETED] Drag & drop batch uploader (multiple PDF files)
│       └── dashboard.html     # [COMPLETED] Recruiter dashboard with stats, search, filters & details drawer
├── candidates.json            # [COMPLETED] Local JSON persistence database for candidate profiles
├── uploads/                   # [COMPLETED] Storage folder for Job Descriptions and Resumes
```

---

## What is Completed (Feature Roadmap)

### 1. Landing/About Page (Phase 1–2) — **100% Complete**
- Built an identical landing page layout resembling the reference design.
- Integrated a custom navigation header, product statistics, and mock resume template previews.
- Modified button handlers to directly launch the screener workflow.

### 2. Multi-Resume Upload & Batch Extraction (Phase 3–4) — **100% Complete**
- Upgraded the home screener page to accept multiple resume PDFs simultaneously.
- Supported text parsing and section mapping using PyMuPDF.

### 3. AI Structured Decision & Reasoning (Phase 5–7) — **100% Complete**
- Integrated Gemini model prompts to analyze resumes against Job Descriptions.
- Configured JSON schemas to return candidate name, score, tier (Strong Fit / Possible Fit / Not Fit), matched/missing skills, strengths, weaknesses, and a **fully audit-ready reasoning justification**.

### 4. Recruiter Dashboard & Details Drawer (Phase 11) — **100% Complete**
- **Summary Cards**: Displays metrics on Total Resumes, Strong Fit, Possible Fit, Not Fit, Scheduled, and Pending candidates.
- **Search Bar**: Allows searching candidates by name.
- **Category Filter Tabs**: Real-time filtering based on Fit tier and Scheduled/Pending states.
- **Candidate Detail Drawer**: Sliding side-drawer revealing candidate statistics, full resume text, matched/missing skills, strengths, weaknesses, and AI rationale.

### 5. Automated Gmail & Calendar Slot Proposer (Phase 8, 10) — **100% Complete**
- Automatically generates 3 business-day interview slots for **Strong Fit** candidates.
- Simulates a Gmail preview with slots and confirmation triggers that instantly schedule and update status records in the database.
- Provides a custom date/time scheduler for other candidate tiers.

### 6. Sample Dataset Loader (Phase 12) — **100% Complete**
- Created a dataset containing **15 realistic candidates** representing diverse edge-cases (Perfect Match, Missing Certifications, Career Switches, Employment Gaps, Poor Formatting, Fresh Graduates, and Keyword Stuffing).
- Interactive dashboard button triggers instant loading of these 15 candidates for immediate live demonstration.
