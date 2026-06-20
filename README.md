# 🚀 Automated Cloud & DevOps Job Scraper

An automated, serverless Python pipeline that scrapes, filters, and scores entry-level Cloud and DevOps job postings, delivering high-quality leads directly to a Google Sheet every morning.

## 🎯 Overview
Finding true entry-level ("fresher") roles in Cloud Computing and DevOps is challenging due to bloated job descriptions and false "entry-level" tags. This project solves that by automatically bypassing standard job board filters and directly parsing the text of job descriptions using Python and Regular Expressions. 

It runs 100% autonomously on a daily schedule using **GitHub Actions**, requiring zero manual intervention and zero hosting costs.

## ✨ Key Features
* **Serverless Automation:** Runs daily via a GitHub Actions Cron job (`1:30 AM UTC`).
* **Smart Filtering:** Uses Regex to immediately reject listings that falsely claim to be entry-level but bury high experience requirements (e.g., "5+ years") in the JD.
* **Tech Stack Scoring:** Parses descriptions to calculate a "Match Score" based on a predefined Cloud/DevOps ecosystem (AWS, Terraform, Kubernetes, Linux, CI/CD).
* **Automated Data Entry:** Integrates securely with the Google Sheets API via a Service Account to log daily leads.
* **Cost-Free Architecture:** Utilizes the free tiers of SerpApi, Google Cloud IAM, and GitHub Actions.

## 🛠️ Technology Stack
* **Language:** Python 3.10
* **Automation:** GitHub Actions (CI/CD workflows)
* **APIs:** * [SerpApi](https://serpapi.com/) (Google Jobs Engine)
  * Google Sheets API & Google Drive API
* **Libraries:** `requests`, `re` (Regex), `gspread`, `oauth2client`

## ⚙️ How It Works
1. **Trigger:** The GitHub Action workflow (`job_scraper.yml`) triggers daily.
2. **Fetch:** The Python script queries the SerpApi for jobs posted in the last 24 hours matching broad tech queries (e.g., "AWS fresher jobs India").
3. **Filter & Score:** * Checks the JD text against a strict `REJECT_EXP_PATTERN` to drop senior roles.
   * Matches keywords to calculate a relevance score based on my core tech stack.
4. **Export:** Securely writes the matching `[Date, Title, Company, Location, Match Score, Apply Link]` to a connected Google Sheet.

## 🔐 Setup & Configuration (For Replication)
If you want to fork this project, you will need to set up the following repository secrets:

1. `SERPAPI_KEY`: Your API key from SerpApi.
2. `GOOGLE_CREDENTIALS`: The complete JSON key from a Google Cloud Service Account with Editor access to your target Google Sheet.

Update the `MY_SKILLS` array and `MINIMUM_SKILL_MATCH` variables in `job_scraper.py` to match your personal technology stack.

## 🤝 Let's Connect
I am a Cloud/
