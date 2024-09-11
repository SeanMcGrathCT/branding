import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import requests
import json
import time

# Define Google Sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('gsheet.json', scope)
client = gspread.authorize(creds)

# Define sheet URLs
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
sheet2_url = 'https://docs.google.com/spreadsheets/d/1V2p0XcGSEYDJHWCL9HsNKRRvfGRvrR-7Tr4kUQVIsfk'

# Open sheets
sheet1 = client.open_by_url(sheet1_url)
sheet2 = client.open_by_url(sheet2_url)

# Load ignored tabs and cache sheet data
ignored_tabs = ['tables', 'Master', 'admin-prov-scores', 'admin-prov-scores_round', 'admin-global', 'Features Matrix', 'Index', 'Consolidated', 'Pages']
cached_sheet_data = {}

def load_all_tabs_into_memory():
    for worksheet in sheet1.worksheets():
        if worksheet.title not in ignored_tabs:
            cached_sheet_data[worksheet.title] = pd.DataFrame(worksheet.get_all_records())

# Function to scrape scores from the URL
def scrape_scores_from_url(url):
    # Example of scraping logic - can be replaced with actual implementation
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Scrape relevant data from the page
    # Example data structure: {'provider': {'am': 10, 'noon': 20, 'pm': 15, 'Average': 15}}
    scraped_scores = {}  # Replace with actual scraped data
    return scraped_scores

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Load URL and mapping data from Sheet 2
    urls_df = pd.DataFrame(sheet2.worksheet('urls').get_all_records())
    mapping_df = pd.DataFrame(sheet2.worksheet('mapping').get_all_records())

    # Scrape scores for the URL
    scraped_scores = scrape_scores_from_url(url)

    # Proceed if scraped scores are available
    if scraped_scores:
        # Mapping logic (using the fuzzy matching logic)
        # Mapping headers would match the scraped scores (e.g., 'am', 'noon', 'pm', 'Average')
        speed_test_data = {
            'am': [51.49, 45.63, 40.91, 52.03, 37.15],  # Example data per provider
            'noon': [50.72, 44.53, 38.91, 49.03, 36.18],
            'pm': [49.99, 46.13, 42.00, 51.03, 35.21],
            'Average': [50.74, 45.43, 40.61, 51.69, 36.85]
        }

        # Generate charts using Chart.js
        st.write("Generating charts...")

        # Example chart data
        labels = ["UK", "US", "Australia", "Italy", "Brazil"]
        datasets = [
            {
                "label": "NordVPN",
                "data": [51.49, 45.63, 40.91, 52.03, 37.15],
                "backgroundColor": "rgba(62, 95, 255, 0.8)",
                "borderColor": "rgba(31, 47, 127, 0.8)",
                "borderWidth": 1
            },
            # Add other providers similarly
        ]

        # HTML for Chart.js
        chart_html = f"""
        <div style="max-width: 805px; margin: 0 auto;">
            <canvas id="speedTestResultsChart" width="805" height="600"></canvas>
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var ctx = document.getElementById('speedTestResultsChart').getContext('2d');
            var speedTestResultsChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: {json.dumps(datasets)}
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 60,
                            title: {{
                                display: true,
                                text: 'Download Speed (Mbps)'
                            }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        """

        # Display chart in Streamlit
        st.components.v1.html(chart_html, height=600)

        # Provide download buttons for .html and .txt versions
        st.download_button("Download Chart as HTML", data=chart_html, file_name="vpn_speed_chart.html", mime="text/html")
        st.download_button("Download Chart as TXT", data=chart_html, file_name="vpn_speed_chart.txt", mime="text/plain")
    else:
        st.write("No data available for the provided URL.")
