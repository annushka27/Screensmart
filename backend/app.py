from flask import Flask, render_template, request, redirect, url_for, jsonify
from parser import extract_text
from gemini_service import analyze_resume
from scheduler import generate_slots
from utils import load_candidates, save_candidates
from dotenv import load_dotenv
import os
import json
import uuid
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(os.path.join(UPLOAD_FOLDER, "resumes"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "jd"), exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def extract_email_from_text(text):
    if not text:
        return None
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if match:
        return match.group(0)
    return None


def send_gmail(to_email, subject, body_text):
    sender_email = os.getenv("GMAIL_EMAIL")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password or "your-email" in sender_email or "xxxx" in app_password:
        reason = "Gmail SMTP credentials not configured or using placeholders."
        print(f"Email failed: {reason}")
        return False, reason

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Success: Email sent to {to_email}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"Email failed: {e}")
        return False, str(e)


@app.route("/")
def home():
    return render_template("about.html")


@app.route("/screener")
def screener():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    resumes = request.files.getlist("resume")
    jd = request.files["jd"]

    jd_path = os.path.join(UPLOAD_FOLDER, "jd", jd.filename)
    jd.save(jd_path)
    jd_text = extract_text(jd_path)

    candidates = load_candidates()

    for resume in resumes:
        if not resume.filename:
            continue
        resume_path = os.path.join(UPLOAD_FOLDER, "resumes", resume.filename)
        resume.save(resume_path)
        
        try:
            resume_text = extract_text(resume_path)
            result = analyze_resume(resume_text, jd_text)
            
            # Determine Tier based on score rules
            score = result.get("score") or 0
            if score >= 85:
                tier = "Strong Fit"
            elif score >= 60:
                tier = "Possible Fit"
            else:
                tier = "Not Fit"

            # Determine initial status
            if tier == "Strong Fit":
                proposed = generate_slots()
                status = "Interview Sent"
                interview_time = ""
            elif tier == "Possible Fit":
                proposed = []
                status = "Pending"
                interview_time = ""
            else:
                proposed = []
                status = "Rejected"
                interview_time = ""

            email_to_use = result.get("email") or result.get("candidate_email") or extract_email_from_text(resume_text)
            if not email_to_use:
                print("Error: Candidate email address is missing from resume.")

            candidate_id = str(uuid.uuid4())
            candidate_data = {
                "id": candidate_id,
                "name": result.get("name") or result.get("candidate_name") or os.path.splitext(resume.filename)[0],
                "email": email_to_use or "candidate@example.com",
                "phone": result.get("phone") or "N/A",
                "score": score,
                "tier": tier,
                "strengths": result.get("strengths") or [],
                "missing_requirements": result.get("missing_requirements") or [],
                "rationale": result.get("rationale") or "No justification provided.",
                "status": status,
                "interview_time": interview_time,
                "proposed_slots": proposed,
                "resume_text": resume_text
            }
            candidates.append(candidate_data)
            save_candidates(candidates)

            if tier == "Strong Fit" and email_to_use:
                role = "Backend Developer"
                subject = f"Interview Invitation: {role} - ScreenSmart Recruitment"
                slots_text = "\n".join([f"📅 {s}" for s in proposed])
                body = f"Dear {candidate_data['name']},\n\nThank you for your application for the {role} position. We reviewed your resume, and your experience aligns strongly with our Job Description.\n\nWe would like to invite you for an interview. Please reply to this email confirming your preference from the following available slots:\n\n{slots_text}\n\nBest regards,\nRecruitment Team\nScreenSmart Suite"
                send_gmail(email_to_use, subject, body)

            # Trigger n8n post-analysis automation webhook if URL is present
            n8n_url = os.getenv("N8N_WEBHOOK_URL")
            if n8n_url:
                try:
                    requests.post(n8n_url, json=candidate_data, timeout=5)
                    print(f"Triggered n8n post-analysis workflow successfully for {candidate_data['name']}.")
                except Exception as n8n_err:
                    print(f"Could not connect to n8n webhook: {n8n_err}")

        except Exception as e:
            print(f"Error parsing resume {resume.filename}: {e}")

    if len(resumes) == 1 and candidates:
        return redirect(url_for("candidate_dashboard", candidate_id=candidates[-1]["id"]))
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    candidates = load_candidates()
    candidates_sorted = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    return render_template("dashboard.html", candidates=candidates_sorted, single_view=False)


@app.route("/dashboard/<candidate_id>")
def candidate_dashboard(candidate_id):
    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        return "Candidate not found", 404
    return render_template("dashboard.html", candidates=[candidate], single_view=True)


@app.route("/send_invite", methods=["POST"])
def send_invite():
    data = request.get_json()
    candidate_id = data.get("id")
    custom_subject = data.get("subject")
    custom_body = data.get("body")

    if not candidate_id:
        return jsonify({"success": False, "error": "Missing candidate id"}), 400

    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == candidate_id), None)
    if not candidate:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    # Build the invitation email with proposed slots
    role = "Backend Developer"
    subject = custom_subject or f"Interview Invitation: {role} - ScreenSmart Recruitment"
    
    if custom_body:
        body = custom_body
    else:
        slots_text = "\n".join([f"📅 {s}" for s in candidate.get("proposed_slots", [])])
        body = f"Dear {candidate['name']},\n\nThank you for your application for the {role} position. We reviewed your resume, and your experience aligns strongly with our Job Description.\n\nWe would like to invite you for an interview. Please reply to this email confirming your preference from the following available slots:\n\n{slots_text}\n\nBest regards,\nRecruitment Team\nScreenSmart Suite"
    
    success, err_msg = send_gmail(candidate["email"], subject, body)
    
    if not success:
        return jsonify({"success": False, "error": f"Email sending failed: {err_msg}"}), 500
        
    candidate["status"] = "Interview Sent"
    save_candidates(candidates)
    
    return jsonify({"success": True, "email_sent": True})


@app.route("/schedule_interview", methods=["POST"])
def schedule_interview():
    data = request.get_json()
    candidate_id = data.get("id")
    interview_time = data.get("time")

    if not candidate_id or not interview_time:
        return jsonify({"success": False, "error": "Missing parameters"}), 400

    candidates = load_candidates()
    updated = False
    for c in candidates:
        if c["id"] == candidate_id:
            c["status"] = "Interview Scheduled"
            c["interview_time"] = interview_time
            updated = True
            
            # Send a real calendar schedule confirmation email!
            role = "Backend Developer"
            subject = f"Interview Confirmed: {role} - ScreenSmart"
            body = f"Dear {c['name']},\n\nYour interview for the {role} position has been scheduled.\n\nDate & Time: {interview_time}\nMeeting Link: https://meet.google.com/abc-defg-hij\n\nBest regards,\nRecruitment Team"
            send_gmail(c['email'], subject, body)
            break

    if updated:
        save_candidates(candidates)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Candidate not found"}), 444


@app.route("/clear_candidates", methods=["POST"])
def clear_candidates():
    save_candidates([])
    return redirect(url_for("home"))


@app.route("/load_samples", methods=["POST"])
def load_samples():
    slots = generate_slots()
    
    samples = [
        {
            "id": "sample-1",
            "name": "Aarav Sharma",
            "email": "aarav@example.com",
            "phone": "555-0199",
            "score": 95,
            "tier": "Strong Fit",
            "rationale": "✓ 5+ years of Java and Spring Boot experience\n✓ Holds active AWS Solution Architect certification\n✓ Built high-performance microservices and REST APIs\n✗ Lacks Docker container configuration details",
            "strengths": ["Microservices design", "Java Spring core expert", "AWS certified"],
            "missing_requirements": ["Docker"],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "Aarav Sharma\nEmail: aarav@example.com\nExperience: 5 years Java / Spring Boot. AWS Solution Architect. Built high-traffic REST APIs."
        },
        {
            "id": "sample-2",
            "name": "Priya Patel",
            "email": "priya@example.com",
            "phone": "555-0143",
            "score": 78,
            "tier": "Possible Fit",
            "rationale": "✓ 3 years of Python and Flask experience\n✓ Strong SQL query optimization skills\n✗ Missing AWS cloud experience\n✗ No Docker/Kubernetes containerization",
            "strengths": ["Excellent Flask backend developer", "Strong SQL query optimization skills"],
            "missing_requirements": ["AWS Certification", "Docker"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Priya Patel\nEmail: priya@example.com\nBackend Developer with 3 years of experience. Stack: Python, Flask, Postgres SQL."
        },
        {
            "id": "sample-3",
            "name": "David Miller",
            "email": "david.m@example.com",
            "phone": "555-0182",
            "score": 71,
            "tier": "Possible Fit",
            "rationale": "✓ 2 years of JavaScript and web development\n✓ Strong database query logic with SQL\n✗ Lacks Python production backend experience\n✗ No cloud native infrastructure experience",
            "strengths": ["High motivation & quick learning curve", "Good database query logic"],
            "missing_requirements": ["Python", "Flask", "AWS"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "David Miller\nEmail: david.m@example.com\nSelf-taught developer. 2 years building frontend apps with React & NodeJS."
        },
        {
            "id": "sample-4",
            "name": "Emma Thompson",
            "email": "emma.t@example.com",
            "phone": "555-0155",
            "score": 88,
            "tier": "Strong Fit",
            "rationale": "✓ 4 years of Python & Flask experience\n✓ Proficient with Docker containerization\n✓ REST API development experience\n✗ Missing cloud provider (AWS) experience\n✗ 1-year career gap (justified by profile)",
            "strengths": ["Proficient in Docker containers", "Excellent database schema design"],
            "missing_requirements": ["AWS"],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "Emma Thompson\nEmail: emma.t@example.com\nSenior Backend Dev. Python, Flask, Docker, Postgres. (Career gap 2024-2025)."
        },
        {
            "id": "sample-5",
            "name": "Robert Chen",
            "email": "rob.c@example.com",
            "phone": "555-0121",
            "score": 68,
            "tier": "Possible Fit",
            "rationale": "✓ 2 years of core Python scripting\n✓ Basic SQL database skills\n✗ Lacks framework (Flask) experience\n✗ Poor resume formatting makes extraction difficult\n✗ Missing containerization/cloud skills",
            "strengths": ["Core python programming knowledge"],
            "missing_requirements": ["Flask", "Docker", "AWS"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Robert Chen - python - sql - db developer - 2 years exp - rob@email.com"
        },
        {
            "id": "sample-6",
            "name": "Aisha Patel",
            "email": "aisha@example.com",
            "phone": "555-0177",
            "score": 70,
            "tier": "Possible Fit",
            "rationale": "✓ Graduate in Computer Science\n✓ Completed Python & REST API internship projects\n✓ Solid SQL foundations\n✗ Missing production-level backend experience\n✗ Missing AWS cloud/Docker experience",
            "strengths": ["High academic record", "Solid data structure foundations"],
            "missing_requirements": ["AWS", "Docker", "Flask"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Aisha Patel\nEmail: aisha@example.com\nFresh Grad CS. Internship at Tech Corp building Python scripts."
        },
        {
            "id": "sample-7",
            "name": "Kevin Vance",
            "email": "kevin@example.com",
            "phone": "555-0112",
            "score": 45,
            "tier": "Not Fit",
            "rationale": "✓ Basic HTML editing skills\n✗ Lacks Python development experience (IT Support background)\n✗ Lacks Flask web framework\n✗ Lacks cloud infrastructure experience\n✗ Keyword stuffing without real project history",
            "strengths": ["Familiar with basic hardware and helpdesk tasks"],
            "missing_requirements": ["Python", "Flask", "AWS", "SQL", "Docker"],
            "status": "Rejected",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Kevin Vance\nSkills: Python AWS Docker Flask Spring Boot Java SQL React Angular\nExperience: IT Support Agent 3 years."
        },
        {
            "id": "sample-8",
            "name": "Clara Barton",
            "email": "clara@example.com",
            "phone": "555-0144",
            "score": 93,
            "tier": "Strong Fit",
            "rationale": "✓ 6 years of Python and Flask development\n✓ Proficient in Docker container setups\n✓ Cloud native deployment on AWS\n✓ Scaled REST APIs\n✗ Lacks TypeScript frontend experience",
            "strengths": ["Full stack versatility", "Advanced database optimization"],
            "missing_requirements": [],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "Clara Barton\nEmail: clara@example.com\n6 years backend dev. Expert in Flask, Python, AWS deployment."
        },
        {
            "id": "sample-9",
            "name": "James Wilson",
            "email": "james@example.com",
            "phone": "555-0188",
            "score": 91,
            "tier": "Strong Fit",
            "rationale": "✓ 12 years backend engineering and system architecture\n✓ Expert with Python, Flask, SQL, Docker, AWS\n✗ Overqualified for this mid-level engineer role",
            "strengths": ["Enterprise systems architecture", "Cloud infrastructure design"],
            "missing_requirements": [],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "James Wilson\nPrincipal Architect. 12 years exp. Expert in Cloud and Backend systems."
        },
        {
            "id": "sample-10",
            "name": "Rahul Robinson",
            "email": "rahul@example.com",
            "phone": "555-0103",
            "score": 35,
            "tier": "Not Fit",
            "rationale": "✓ 4 years SQL experience\n✗ Wrong stack (exclusive PHP/WordPress development)\n✗ No Python or Flask backend experience\n✗ No containerization (Docker) or AWS cloud experience",
            "strengths": ["CMS development"],
            "missing_requirements": ["Python", "Flask", "Docker", "AWS"],
            "status": "Rejected",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Rahul Robinson\nWordPress and PHP expert. 4 years building plugins."
        },
        {
            "id": "sample-11",
            "name": "Linus Torvalds",
            "email": "linus@example.com",
            "phone": "555-0190",
            "score": 90,
            "tier": "Strong Fit",
            "rationale": "✓ 20+ years low-level systems architecture\n✓ Expert in Docker configurations and Linux\n✓ Strong SQL database knowledge\n✗ Lacks Flask web framework specific experience",
            "strengths": ["Low-level systems expertise", "Docker configuration master"],
            "missing_requirements": ["Flask"],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "Linus Torvalds\nLinux Founder. Git Creator. Systems Architect."
        },
        {
            "id": "sample-12",
            "name": "Chloe Adams",
            "email": "chloe@example.com",
            "phone": "555-0161",
            "score": 64,
            "tier": "Possible Fit",
            "rationale": "✓ B.S. CS Graduate\n✓ Basic Python project experience\n✗ Zero full-time production engineering experience\n✗ Missing Flask frameworks\n✗ Missing Docker/AWS cloud deployments",
            "strengths": ["Academically strong in database design"],
            "missing_requirements": ["Flask", "Docker", "AWS"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Chloe Adams\nRecent CS Graduate. Familiar with Python scripting."
        },
        {
            "id": "sample-13",
            "name": "Arthur Pendragon",
            "email": "arthur@example.com",
            "phone": "555-0125",
            "score": 40,
            "tier": "Not Fit",
            "rationale": "✓ Basic HTML familiarity\n✗ Career changer (History teacher)\n✗ Only 2-week coding bootcamp experience\n✗ Lacks engineering foundation and backend skills",
            "strengths": ["Great communication and leadership"],
            "missing_requirements": ["Python", "Flask", "Docker", "AWS", "SQL"],
            "status": "Rejected",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Arthur Pendragon\nFormer History Teacher. Coding Bootcamp graduate."
        },
        {
            "id": "sample-14",
            "name": "Jessica Alba",
            "email": "jessica@example.com",
            "phone": "555-0130",
            "score": 76,
            "tier": "Possible Fit",
            "rationale": "✓ 3 years React and frontend JavaScript experience\n✓ REST API integration skills\n✗ Lacks Python development skills\n✗ Missing backend framework (Flask) experience\n✗ Lacks database and SQL design",
            "strengths": ["Stellar frontend interfaces", "REST API integration experience"],
            "missing_requirements": ["Python", "Flask", "SQL"],
            "status": "Pending",
            "interview_time": "",
            "proposed_slots": [],
            "resume_text": "Jessica Alba\nFrontend Developer. Stack: React, JavaScript, APIs."
        },
        {
            "id": "sample-15",
            "name": "Bruce Wayne",
            "email": "bruce@example.com",
            "phone": "555-0100",
            "score": 96,
            "tier": "Strong Fit",
            "rationale": "✓ 8 years secure cloud systems engineering\n✓ Expert in Python, Flask, Docker, AWS\n✓ Built secure REST APIs\n✓ Flawless technical alignment with JD",
            "strengths": ["Advanced cloud security architectures", "Flawless technical matching"],
            "missing_requirements": [],
            "status": "Interview Scheduled",
            "interview_time": slots[0],
            "proposed_slots": slots,
            "resume_text": "Bruce Wayne\nEmail: WayneTech@Gotham.com\n8 years building secure cloud APIs. Python, AWS, Docker."
        }
    ]
    
    save_candidates(samples)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)