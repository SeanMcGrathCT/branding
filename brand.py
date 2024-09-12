import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import zipfile
import io

# Google Sheets API setup
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "your_sheet_id_here"
RANGE_NAME = "Consolidated!A:Z"

# Function to fetch data from Google Sheets
def fetch_sheet_data(sheet_id, range_name):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE)
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    return pd.DataFrame(values[1:], columns=values[0])  # Convert to DataFrame

# Fetch Google Sheets data
sheet_data = fetch_sheet_data(SHEET_ID, RANGE_NAME)

# Display the data preview
st.write("Data Preview")
st.dataframe(sheet_data)

# Fuzzy matching function to identify relevant columns
def fuzzy_match_columns(df, keywords):
    matched_cols = {}
    for keyword in keywords:
        matched_col, score = process.extractOne(keyword, df.columns, scorer=fuzz.partial_ratio)
        if score > 80:  # Threshold for matching
            matched_cols[keyword] = matched_col
    return matched_cols

# Define keywords for speed tests and overall score
speed_test_keywords = ["a.m.", "noon", "p.m.", "average"]
overall_score_keywords = ["Overall Score"]

# Perform fuzzy matching on columns
matched_speed_cols = fuzzy_match_columns(sheet_data, speed_test_keywords)
matched_overall_cols = fuzzy_match_columns(sheet_data, overall_score_keywords)

st.write("Matched Speed Test Columns:", matched_speed_cols)
st.write("Matched Overall Score Columns:", matched_overall_cols)

# Function to generate chart.js HTML
def generate_chart_js(chart_id, labels, dataset, chart_title, y_label):
    chart_js = f"""
    <div style="max-width: 500px; margin: 0 auto;">
        <canvas class='jschartgraphic' id="{chart_id}" width="500" height="300"></canvas>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var ctx = document.getElementById('{chart_id}').getContext('2d');
            var {chart_id} = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '{chart_title}',
                        data: {json.dumps(dataset)},
                        backgroundColor: 'rgba(62, 95, 255, 0.8)',
                        borderColor: 'rgba(62, 95, 255, 0.8)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: '{y_label}'
                            }}
                        }}
                    }},
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{chart_title}'
                        }}
                    }}
                }}
            }});
        }});
    </script>
    """
    return chart_js

# Generate charts for each provider's speed tests
provider_names = sheet_data['VPN Provider'].unique()

chart_js_files = []
for provider in provider_names:
    provider_data = sheet_data[sheet_data['VPN Provider'] == provider]
    labels = ["UK (a.m.)", "UK (noon)", "UK (p.m.)"]
    speed_tests = [provider_data[col].values[0] for col in matched_speed_cols.values()]
    
    chart_id = f"{provider}_SpeedChart"
    chart_title = f"{provider} Speed Test (Mbps)"
    chart_js = generate_chart_js(chart_id, labels, speed_tests, chart_title, "Speed (Mbps)")
    
    # Save chart JS to list
    chart_js_files.append((f"{provider}_speed_chart.txt", chart_js))

# Generate comparison chart for Overall Scores
overall_scores = [sheet_data[col].values[0] for col in matched_overall_cols.values()]
overall_chart_js = generate_chart_js("Overall_Score_Chart", provider_names, overall_scores, "VPN Providers Overall Score", "Score")

chart_js_files.append(("overall_score_chart.txt", overall_chart_js))

# Zip and download the charts
if st.button("Download Charts as Zip"):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for filename, content in chart_js_files:
            zf.writestr(filename, content)
    
    st.download_button(label="Download Zip", data=zip_buffer.getvalue(), file_name="charts.zip", mime="application/zip")
