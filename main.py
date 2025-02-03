import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd
import time
from io import StringIO

# Configure Streamlit page
st.set_page_config(page_title="AI Investment Scout", layout="wide")
st.title("🔍 AI-Powered Investment Lead Finder")

# Custom CSS for better styling
st.markdown("""
<style>
    .reportview-container {background: #f5f5f5}
    .stDataFrame {border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1)}
    .stDownloadButton button {background-color: #4CAF50; color: white}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'search_made' not in st.session_state:
    st.session_state.search_made = False

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    SERPAPI_KEY = st.text_input("SerpAPI Key", type="password")
    GEMINI_API_KEY = st.text_input("Gemini API Key", type="password")
    st.markdown("---")
    st.header("🛠️ Features")
    enable_cache = st.checkbox("Enable Caching", value=True)
    sample_mode = st.checkbox("Sample Mode (No API Needed)")

# Main input section
col1, col2 = st.columns([3, 1])
with col1:
    sector = st.text_input("Enter target sector:", "Automobile").strip()
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("Find Investment Leads")

# Cached function for API calls
@st.cache_data(show_spinner=False, ttl=3600 if enable_cache else 0)
def fetch_and_process_data(_sector, serpapi_key, gemini_key):
    # Configure Gemini
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-pro')
    
    # Date calculations
    date_range = {
        'start': (datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y'),
        'end': datetime.now().strftime('%m/%d/%Y')
    }
    
    # SerpAPI call
    params = {
        "q": f"{_sector} company expansion investment new plant setup -job -career",
        "hl": "en",
        "gl": "in",
        "api_key": serpapi_key,
        "tbs": f"cdr:1,cd_min:{date_range['start']},cd_max:{date_range['end']}"
    }
    
    response = requests.get("https://serpapi.com/search", params=params)
    raw_data = response.json()
    
    # Process results
    processed = []
    if "organic_results" in raw_data:
        for result in raw_data["organic_results"]:
            # Rate limiting
            time.sleep(1)  # Avoid API flooding
            
            try:
                prompt = f"""Extract investment details from:
                Title: {result.get('title', '')}
                Summary: {result.get('snippet', '')}
                URL: {result.get('link', '')}

                Return format:
                Company Name | Investment Plan | Source URL
                - If irrelevant, return 'None|None|None'"""
                
                response = model.generate_content(prompt)
                parts = response.text.strip().split('|')
                
                if len(parts) == 3 and 'None' not in parts[0]:
                    processed.append({
                        'Company': parts[0].strip(),
                        'Investment Plan': parts[1].strip(),
                        'Source URL': parts[2].strip()
                    })
            except Exception as e:
                continue
    
    return processed

# Sample data for demo mode
SAMPLE_DATA = [
    {'Company': 'Tata Motors', 
     'Investment Plan': 'Planning $1B EV battery plant in Maharashtra by 2025',
     'Source URL': 'https://example.com/tata-motors'},
    {'Company': 'Reliance Chemicals',
     'Investment Plan': 'New petrochemical complex announcement in Gujarat',
     'Source URL': 'https://example.com/reliance-chemicals'}
]

# Main processing logic
if search_clicked:
    if sample_mode:
        results = SAMPLE_DATA
        st.session_state.search_made = True
    else:
        if not SERPAPI_KEY or not GEMINI_API_KEY:
            st.error("🔑 Please provide both API keys!")
            st.stop()
        
        try:
            with st.spinner("🚀 Scanning global investment opportunities..."):
                results = fetch_and_process_data(
                    sector, SERPAPI_KEY, GEMINI_API_KEY
                )
                st.session_state.search_made = True
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
            st.stop()

    if st.session_state.search_made:
        if results:
            df = pd.DataFrame(results)
            
            # Display results
            st.success(f"✅ Found {len(df)} investment leads in {sector}")
            
            # Dataframe display
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Source URL": st.column_config.LinkColumn(
                        "Source", display_text="Open Link"
                    )
                },
                hide_index=True
            )
            
            # CSV Export
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv_buffer.getvalue(),
                file_name=f"{sector}_investment_leads.csv",
                mime="text/csv"
            )
        else:
            st.warning("🤷 No relevant investment leads found")

# Add footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Powered by SerpAPI, Google Gemini, and Streamlit</p>
    <p>Note: Results are based on publicly available web data</p>
</div>
""", unsafe_allow_html=True)
