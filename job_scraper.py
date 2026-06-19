import os
import re
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

JOB_TITLES = [
    "Cloud Support Engineer", "AWS Cloud Support Associate", "Cloud Infrastructure Support Engineer",
    "L1/L2 AWS Cloud Operations Support", "Cloud Operations Associate", "Application Support Engineer",
    "IT Operations Analyst", "Cloud Operations Analyst", "Platform Support Engineer", "Junior Cloud Engineer",
    "Junior Infrastructure Engineer", "Junior Cloud Infrastructure Engineer", "Systems Administrator (Junior)",
    "Linux Support Engineer", "DevOps Engineer", "NOC Engineer", "Monitoring Engineer", "AWS Cloud"
]

KEYWORD_RULES = ["AWS", "Cloud", "DevOps", "Monitoring"]

MY_SKILLS = [
    "aws", "ec2", "s3", "vpc", "lambda", "cloudformation", "route 53", "eks", "rds", "alb", "dms", "ses", 
    "secrets manager", "sns", "sqs", "cloudwatch", "terraform", "ansible", "kubernetes", "deployments", 
    "replicasets", "statefulsets", "daemonsets", "namespaces", "services", "configmaps", "secrets", 
    "ingress", "argocd", "istio", "helm", "docker", "github actions", "oidc", "git", "trivy", 
    "sonarqube", "prometheus", "grafana", "linux", "mysql", "subnetting", "networking"
]

# STRICT FILTER: Rejects anything explicitly demanding 2, 3, 4, 5+ years to protect against false entries
REJECT_EXP_PATTERN = re.compile(
    r'(?:\b(?:2|3|4|5|6|7|8|9|10)\+?\s*(?:-\s*(?:\d+))?\s*(?:years?|yrs?)\b|\bminimum\s*(?:2|3|4|5)\b)', 
    re.IGNORECASE
)

# Explicitly accepts true fresher indicators
ACCEPT_EXP_PATTERN = re.compile(
    r'\b(?:0|1|6\s*months)\s*(?:to|-)?\s*(?:1)?\s*(?:years?|yrs?)\b|\b(?:fresher|entry[- ]level|graduate|no\s*experience\s*required)\b', 
    re.IGNORECASE
)

def evaluate_job(title, description):
    desc_lower = description.lower()
    
    # 1. Strict Experience Gatekeeping
    if REJECT_EXP_PATTERN.search(desc_lower):
        # If it contains a mid-level year requirement, drop it unless it explicitly mentions it's open to freshers
        if not ACCEPT_EXP_PATTERN.search(desc_lower):
            return False, 0
            
    # 2. Skill-Matching Analysis
    matched_skills = [skill for skill in MY_SKILLS if skill in desc_lower]
    match_percentage = (len(matched_skills) / len(MY_SKILLS)) * 100
    
    # Needs to hit a baseline of at least 4 tech keywords from your stack
    is_highly_relevant = len(matched_skills) >= 4
    
    return is_highly_relevant, round(match_percentage, 2)

def fetch_jobs_from_api(api_key):
    all_jobs = []
    seen_job_ids = set()
    
    # Query a batch of titles daily.
    for title in JOB_TITLES[:5]:  
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{title} jobs India",
            "chips": "date:today",  # <--- CRITICAL FIX: Restricts results strictly to the last 24 hours
            "api_key": api_key,
            "hl": "en"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            jobs = data.get("jobs_results", [])
            
            for job in jobs:
                job_id = job.get("job_id")
                if job_id and job_id not in seen_job_ids:
                    seen_job_ids.add(job_id)
                    all_jobs.append(job)
        except Exception as e:
            print(f"Error fetching {title}: {e}")
            
    return all_jobs

def update_google_sheet(qualified_jobs):
    if not qualified_jobs:
        print("No new qualified jobs found matching criteria today.")
        return

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open("Job Tracker").worksheet("Jobs")
    today = datetime.now().strftime("%Y-%m-%d")
    
    existing_links = sheet.col_values(6)
    
    added_count = 0
    for job in qualified_jobs:
        if job['link'] in existing_links:
            continue
            
        sheet.append_row([
            today,
            job['title'],
            job['company'],
            job['location'],
            f"{job['match_score']}%",
            job['link']
        ])
        added_count += 1
        
    print(f"Successfully appended {added_count} new unique jobs to Google Sheets!")

def main():
    SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
    if not SERPAPI_KEY:
        print("Missing SERPAPI_KEY environment variable.")
        return

    print("Fetching brand new job postings (past 24h)...")
    raw_jobs = fetch_jobs_from_api(SERPAPI_KEY)
    
    qualified_jobs = []
    for job in raw_jobs:
        title = job.get("title", "")
        company = job.get("company_name", "")
        description = job.get("description", "")
        location = job.get("location", "Not Specified")
        
        # Link extraction fix handling both schemas safely
        apply_options = job.get("apply_options", [])
        if apply_options:
            apply_link = apply_options[0].get("link", "No link")
        else:
            apply_link = job.get("related_links", [{}])[0].get("link", "No link")
        
        title_lower = title.lower()
        has_valid_title = any(kw.lower() in title_lower for kw in KEYWORD_RULES) or any(t.lower() in title_lower for t in JOB_TITLES)
        
        if not has_valid_title:
            continue
            
        is_match, match_score = evaluate_job(title, description)
        
        if is_match:
            qualified_jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "match_score": match_score,
                "link": apply_link
            })

    qualified_jobs = sorted(qualified_jobs, key=lambda x: x['match_score'], reverse=True)
    update_google_sheet(qualified_jobs)

if __name__ == "__main__":
    main()
