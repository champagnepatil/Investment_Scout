import time
import streamlit as st
import requests
import json
import os
import datetime
import google.generativeai as genai
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Investment Leads Identifier",
    page_icon="💼",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { padding: 2rem; }
    .stButton button { width: 100%; }
    .result-card { padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; border: 1px solid #ddd; }
    .company-name { font-size: 1.2rem; font-weight: bold; }
    .source-link { font-style: italic; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.title("Investment Leads Identifier")
st.subheader("Find companies planning expansion or investments in your target sector")
st.markdown("""
This tool helps identify potential investment leads by:
1. Searching for recent news about company expansions in your sector
2. Processing the results to extract relevant information
3. Presenting a curated list of potential investment opportunities
""")

# Function to get search results from SerpAPI
def get_search_results(sector, date_range=None):
    try:
        serpapi_key = os.environ.get("SERPAPI_API_KEY")
        if not serpapi_key:
            st.error("SerpAPI key not found. Please set the SERPAPI_API_KEY environment variable.")
            return None
        
        # Calculate date range if not provided
        if not date_range:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
        
        # Construct search query
        search_query = f"{sector} company expansion investment new plant setup -job -career -vacancy"
        
        params = {
            "engine": "google",
            "q": search_query,
            "api_key": serpapi_key,
            "tbs": "qdr:m2",  # Last 2 months
            "num": 5  # Reduced number of results
        }
        
        with st.spinner("Searching for relevant company news..."):
            response = requests.get("https://serpapi.com/search", params=params)
            if response.status_code != 200:
                st.error(f"Error querying SerpAPI: {response.status_code}")
                logger.error(f"SerpAPI error: {response.text}")
                return None
            
            results = response.json()
            if "organic_results" not in results:
                st.warning("No results found. Try a different sector or broader search terms.")
                return []
            
            return results["organic_results"]
            
    except Exception as e:
        st.error(f"Error occurred while fetching search results: {str(e)}")
        logger.exception("Error in get_search_results")
        return None

# Function to process results using Gemini with exponential backoff
def process_with_gemini(result, sector, max_retries=3):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        st.error("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
        return None

    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    title = result.get("title", "")
    snippet = result.get("snippet", "")
    link = result.get("link", "")
    
    prompt = f"""
    You are an AI assistant working for an investment promotion agency in Maharashtra. Your task is to analyze Google search results
    and extract relevant information about top companies in the specified sector. Review this search result about potential company expansion or investment in the {sector} sector:
    
    Title: {title}
    Snippet: {snippet}
    Link: {link}
    
    Extract the following information:
    1. Company name (if mentioned)
    2. Summary of the company's investment or expansion plans
    3. The source URL
    
    If this result is about job postings, career opportunities, or is unrelated to company expansion/investment, return exactly: {{"result": "Irrelevant"}}
    
    Otherwise, return a JSON with this structure:
    {{
        "company_name": "Name of the company",
        "investment_summary": "Brief summary of the expansion or investment plans",
        "source_url": "{link}"
    }}
    
    Only return the JSON, without any additional text or explanation.
    """
    
    retry_count = 0
    retry_delay = 2  # Start with a 2-second delay
    
    while retry_count < max_retries:
        try:
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Remove markdown formatting if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed_response = json.loads(response_text)
            return parsed_response
        
        except Exception as e:
            if "429" in str(e) and retry_count < max_retries - 1:
                st.warning(f"Rate limit hit, retrying in {retry_delay} seconds...")
                logger.warning(f"Retry {retry_count+1} due to error: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                retry_count += 1
            else:
                st.error(f"Error processing result with Gemini: {str(e)}")
                logger.exception("Error in process_with_gemini")
                return None
    return None

def main():
    # Sidebar for inputs
    with st.sidebar:
        st.header("Search Parameters")
        sector = st.text_input("Enter Industry/Sector", "Automobile")
        
        st.subheader("Advanced Options")
        use_custom_date = st.checkbox("Use custom date range", False)
        
        if use_custom_date:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            start_date = st.date_input("Start date", start_date)
            end_date = st.date_input("End date", end_date)
            
            if start_date > end_date:
                st.error("Start date must be before end date")
                return
            
            date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
        else:
            date_range = None
        
        search_button = st.button("Search for Leads")
    
    if search_button:
        if not sector:
            st.error("Please enter an industry or sector")
            return
        
        # Step 1: Get search results
        results = get_search_results(sector, date_range)
        if not results:
            return
        
        # Step 2 & 3: Process results with Gemini
        processed_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, result in enumerate(results):
            status_text.text(f"Processing result {i+1} of {len(results)}...")
            processed_result = process_with_gemini(result, sector)
            if processed_result and processed_result.get("result") != "Irrelevant":
                processed_results.append(processed_result)
            
            progress_bar.progress((i + 1) / len(results))
            time.sleep(2)  # Delay between each API call
        
        progress_bar.empty()
        status_text.empty()
        
        # Step 4: Display results
        if processed_results:
            st.subheader(f"Investment Leads in {sector} Sector")
            st.write(f"Found {len(processed_results)} potential leads")
            
            results_df = []
            for result in processed_results:
                if "company_name" in result and "investment_summary" in result:
                    results_df.append({
                        "Company": result.get("company_name", "Unknown"),
                        "Investment Plans": result.get("investment_summary", ""),
                        "Source": f"[Link]({result.get('source_url', '')})"
                    })
            
            if results_df:
                st.table(results_df)
                st.download_button(
                    label="Download Results as CSV",
                    data="\n".join([
                        "Company,Investment Plans,Source",
                        *[f'"{r["Company"]}","{r["Investment Plans"]}","{r["Source"]}"' for r in results_df]
                    ]),
                    file_name=f"{sector}_investment_leads_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No leads were found after filtering. Try broadening your search criteria.")
        else:
            st.warning("No relevant investment leads found. Try a different sector or broaden your search terms.")

if __name__ == "__main__":
    main()
