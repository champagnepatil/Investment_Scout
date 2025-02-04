import os
import json
import requests
import streamlit as st
from datetime import datetime, timedelta
import google.generativeai as genai

# --- CONFIGURATION ---
# Replace these with your actual API keys or set them as environment variables.
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "68b24d5fd2ad3ca86d86896c0a63cca3b2bdb67c63732e90c5ff87d06e805039")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBb4zXQO1XelsydxGRny-UHZN_ZznhAB0g")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

st.title("Investment Promotion Agency - Company Expansion Leads")

# --- USER INPUT ---
sector = st.text_input("Enter Sector (e.g., Automobile)", value="Automobile")

if st.button("Search"):
    with st.spinner("Searching for leads..."):
        # --- STEP 1: Query SERPAPI ---
        query = f"{sector} company expansion investment new plant setup -job -career"

        # Calculate the date 2 months ago and the current date in MM/DD/YYYY format
        two_months_ago = (datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y')
        current_date = datetime.now().strftime('%m/%d/%Y')

        # Define SERPAPI parameters with a custom date range
        params = {
            "q": query,
            "hl": "en",
            "gl": "in",  # Adjust the country code as needed.
            "api_key": SERPAPI_KEY,
            "tbs": f"cdr:1,cd_min:{two_months_ago},cd_max:{current_date}"
        }

        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()

        # Extract raw search results
        raw_results = []
        if "organic_results" in data:
            for result in data["organic_results"]:
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No summary available")
                link = result.get("link", "No URL available")
                raw_results.append({
                    "title": title,
                    "snippet": snippet,
                    "link": link
                })

        # --- STEP 2: Refine Results Using Gemini ---
        refined_results = []  # List to hold the refined JSON results.
        for result in raw_results:
            prompt = f"""
You are an AI assistant helping an investment promotion agency identify companies planning investments or expansions.
Analyze the following search result and extract only the relevant information. Return your output as a valid JSON object with the following keys:
- "company_name": The name of the company (if mentioned).
- "investment_plan": A summary of their investment or expansion plans.
- "source_url": The source URL.

Search Result:
Title: {result['title']}
Summary: {result['snippet']}
URL: {result['link']}

If the result is irrelevant (e.g., job postings, unrelated news), return: {{"result": "Irrelevant"}}
"""
            try:
                gemini_response = model.generate_content(prompt)
                refined_text = gemini_response.text.strip()
                refined_data = json.loads(refined_text)
                # Skip if marked as irrelevant
                if refined_data.get("result", "").lower() == "irrelevant":
                    continue
                refined_results.append(refined_data)
            except Exception as e:
                st.error(f"Error processing a result: {e}")
                continue

        # --- STEP 3: Display the Results As-Is ---
        if refined_results:
            st.success(f"Found {len(refined_results)} relevant lead(s):")
            for i, result in enumerate(refined_results, 1):
                st.write(f"**Lead {i}:**")
                st.json(result)
        else:
            st.info("No relevant leads found.")
