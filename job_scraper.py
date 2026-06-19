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

# Strict filters: eliminates listings demanding mid-to-senior levels (5+ years)
REJECT_EXP_PATTERN = re.compile(
    r'(?:\b(?:5|6|7|8|9|10|11|12)\+?\s*(?:-\s*(?:\d+))?\s*(?:years?|yrs?)\b|\bminimum\s*(?:5|6|7|8|9|10)\b)', 
    re.IGNORECASE
)

# Accepts specific fresher timelines (0 to 4 years)
ACCEPT_EXP_PATTERN = re.compile(
    r'\b(?:0|1|2|3|4|6\s*months)\s*(?:to|-)?\s*(?:1|2|3|4)?\s*(?:years?|yrs?)\b|\b(?:fresher|entry[- ]level|graduate)\b', 
    re.IGNORECASE
)

def evaluate_job(title, description):
    desc_lower = description.lower()
    
    if REJECT_EXP_PATTERN.search(desc_lower):
        if not ACCEPT_EXP_PATTERN.search(desc_lower):
            return False, 0
            
    matched_skills = [skill for skill in MY_SKILLS if skill in desc_lower]
    match_percentage = (len(matched_skills) / len(MY_SKILLS)) * 100
    
    # Valid matching logic if it contains elements of your technology ecosystem
    is_highly_relevant = len(matched_skills) >= 4
    
    return is_highly_relevant, round(match_percentage, 2)

def fetch_jobs_from_api(api_key):
    all_jobs = []
    seen_job_ids = set()
    
    # We rotate through the first few titles to stay safely within the free 100 monthly queries limit
    # You can change the slice daily or run specific subsets
    for title in JOB_TITLES[:4]:  
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{title} jobs India",
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
    
    # Extract existing links to avoid duplicate entries
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

    print("Fetching job postings...")
    raw_jobs = fetch_jobs_from_api(SERPAPI_KEY)
    
    qualified_jobs = []
    for job in raw_jobs:
        title = job.get("title", "")
        company = job.get("company_name", "")
        description = job.get("description", "")
        location = job.get("location", "Not Specified")
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
