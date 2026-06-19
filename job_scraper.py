import os
import re
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Replaced specific job titles with broad technical search queries
BROAD_SEARCH_QUERIES = [
    "AWS fresher jobs India", 
    "Cloud entry level jobs India", 
    "DevOps entry level jobs India",
    "DevOps fresher jobs India",
    "NOC entry level jobs India"
]

MY_SKILLS = [
    "aws", "ec2", "s3", "vpc", "lambda", "cloudformation", "route 53", "eks", "rds", "alb", "dms", "ses", 
    "secrets manager", "sns", "sqs", "cloudwatch", "terraform", "ansible", "kubernetes", "deployments", 
    "replicasets", "statefulsets", "daemonsets", "namespaces", "services", "configmaps", "secrets", 
    "ingress", "argocd", "istio", "helm", "docker", "github actions", "oidc", "git", "trivy", 
    "sonarqube", "prometheus", "grafana", "linux", "mysql", "subnetting", "networking"
]

# CHANGE THIS NUMBER if your sheet stays empty. 6 is very strict for a fresher JD.
MINIMUM_SKILL_MATCH = 6

# Strict filter: Rejects anything explicitly demanding 2, 3, 4, 5+ years
REJECT_EXP_PATTERN = re.compile(
    r'(?:\b(?:3|4|5|6|7|8|9|10)\+?\s*(?:-\s*(?:\d+))?\s*(?:years?|yrs?)\b|\bminimum\s*(?:2|3|4|5)\b)', 
    re.IGNORECASE
)

# Explicitly accepts true fresher indicators
ACCEPT_EXP_PATTERN = re.compile(
    r'\b(?:0|1|2|6\s*months)\s*(?:to|-)?\s*(?:1)?\s*(?:years?|yrs?)\b|\b(?:fresher|entry[- ]level|graduate|no\s*experience\s*required)\b', 
    re.IGNORECASE
)

def evaluate_job(description):
    desc_lower = description.lower()
    
    # 1. Strict Experience Gatekeeping
    if REJECT_EXP_PATTERN.search(desc_lower):
        if not ACCEPT_EXP_PATTERN.search(desc_lower):
            return False, 0
            
    # 2. Heavy Skill-Matching Analysis
    matched_skills = [skill for skill in MY_SKILLS if skill in desc_lower]
    match_percentage = (len(matched_skills) / len(MY_SKILLS)) * 100
    
    # Needs to hit your new threshold of 8 specific keywords
    is_highly_relevant = len(matched_skills) >= MINIMUM_SKILL_MATCH
    
    return is_highly_relevant, round(match_percentage, 2)

def fetch_jobs_from_api(api_key):
    all_jobs = []
    seen_job_ids = set()
    
    # Loop through the new broad technical queries
    for query in BROAD_SEARCH_QUERIES:  
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": query,
            # We are keeping the 1 week limit to ensure fresh postings
            "chips": "date:week",  
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
            print(f"Error fetching {query}: {e}")
            
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

    print("Fetching broad tech job postings (past 24h)...")
    raw_jobs = fetch_jobs_from_api(SERPAPI_KEY)
    
    qualified_jobs = []
    for job in raw_jobs:
        title = job.get("title", "")
        company = job.get("company_name", "")
        description = job.get("description", "")
        location = job.get("location", "Not Specified")
        
        apply_options = job.get("apply_options", [])
        if apply_options:
            apply_link = apply_options[0].get("link", "No link")
        else:
            apply_link = job.get("related_links", [{}])[0].get("link", "No link")
        
        # We removed the Title validation check here. It now strictly relies on JD evaluation.
        is_match, match_score = evaluate_job(description)
        
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
