def get_analysis_prompt(resume_text, jd_text):
    return f"""
You are an expert recruiter and ATS Resume Analyzer.

Compare the Resume and Job Description.

Return ONLY valid JSON.

Scoring Rules:
- 85-100: Strong Fit
- 60-84: Possible Fit
- Below 60: Not Fit

Prompt instructions:
1. Carefully extract matching and missing requirements.
2. In the "rationale" field, write an auditable, evidence-based reason structured with:
   - Checkmarks (✓) for met requirements matching specific resume content (e.g., ✓ 4 years Python experience)
   - Crosses (✗) for missing requirements (e.g., ✗ AWS certification missing)
   No generic "good fit" descriptions. Give specific evidence.

JSON output structure:

{{
    "name":"John Doe",
    "email":"john.doe@example.com",
    "phone":"123-456-7890",
    "score":87,
    "tier":"Strong Fit",
    "strengths":[
        "4 years Python",
        "Flask",
        "SQL"
    ],
    "missing_requirements":[
        "AWS Certification"
    ],
    "rationale":"✓ 4 years Python experience\n✓ Knows Flask and SQL\n✗ Missing AWS Certification",
    "status":"Pending"
}}

Job Description:

{jd_text}

Resume:

{resume_text}
"""
