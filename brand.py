import streamlit as st
import pandas as pd
import json
from fuzzywuzzy import process
import zipfile
import io
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

# Access the service account credentials from secrets
credentials_info = st.secrets["gsheet_service_account"]

# Define the scope and load credentials from secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Open the Google Sheet
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
try:
    sheet1 = client.open_by_url(sheet1_url)
    st.success("Successfully opened the Google Sheet.")
except Exception as e:
    st.error(f"Failed to open Google Sheet: {e}")

# Load the 'Consolidated' worksheet
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Convert the data to a pandas DataFrame
columns = consolidated_data[0]  # Headers
rows = consolidated_data[1:]  # Data rows
sheet_data = pd.DataFrame(rows, columns=columns)

# Coerce all data to strings to avoid type-related errors
sheet_data = sheet_data.astype(str)

# Display the shape and first 10 rows of the data to check
st.write("Shape of the DataFrame:", sheet_data.shape)
st.write("Data Types of Each Column:", sheet_data.dtypes)
st.dataframe(sheet_data.head(10))  # Display first 10 rows


# Fuzzy matching function to identify relevant columns
def fuzzy_match_columns(df, keywords):
    matched_cols = {}
    for keyword in keywords:
        matched_col, score = process.extractOne(keyword, df.columns)
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
