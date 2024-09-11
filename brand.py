import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import requests
import json

# Access the service account credentials from secrets
credentials_info = st.secrets["gsheet_service_account"]

# Define the scope and load credentials from secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Define sheet URLs
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
sheet2_url = 'https://docs.google.com/spreadsheets/d/1V2p0XcGSEYDJHWCL9HsNKRRvfGRvrR-7Tr4kUQVIsfk'

# Open the Google Sheets
sheet1 = client.open_by_url(sheet1_url)
sheet2 = client.open_by_url(sheet2_url)

# List of ignored tabs
ignored_tabs = ['tables', 'Master', 'admin-prov-scores', 'admin-prov-scores_round', 'admin-global', 
                'Features Matrix', 'Index', 'Consolidated', 'Pages']

# Function to find the correct tab based on the URL in A1
def find_tab_by_url(sheet, url):
    for worksheet in sheet.worksheets():
        if worksheet.title not in ignored_tabs:
            # Get the value in cell A1 of the current worksheet
            a1_value = worksheet.acell('A1').value
            if a1_value and a1_value.strip() == url:
                return worksheet
    return None

# Function to scrape scores from the URL (this is a placeholder, you can add your actual scraping logic)
def scrape_scores_from_url(url):
    # Example: You would implement the real scraping logic here
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    scraped_scores = {
        'am': 50,
        'noon': 45,
        'pm': 48,
        'Average': 47
    }
    return scraped_scores

# Function to map headers and find relevant data
def map_headers_and_extract_data(sheet, url):
    # Load the 'mapping' tab from sheet2
    mapping_sheet = sheet2.worksheet('mapping')
    mapping_data = pd.DataFrame(mapping_sheet.get_all_records())
    
    # Filter mapping data by the given URL
    filtered_mapping = mapping_data[mapping_data['URL'] == url]
    
    if not filtered_mapping.empty:
        st.write(f"Found {len(filtered_mapping)} matching rows in the mapping sheet.")
        
        # Extract relevant mappings for the given URL
        scraped_score_names = filtered_mapping['Scraped Score Name'].tolist()
        mapped_headers = filtered_mapping['Mapped Header'].tolist()
        
        # Find the correct worksheet in sheet1 using the URL
        matching_tab = find_tab_by_url(sheet1, url)
        
        if matching_tab:
            st.write(f"Found matching tab: {matching_tab.title}")
            
            # Get all headers from row 2 in the matching tab
            headers = matching_tab.row_values(2)
            
            # Create a dictionary to map the Mapped Headers to their index positions
            header_indices = {header: index for index, header in enumerate(headers)}
            
            # Extract the data for the matched headers
            extracted_data = []
            for mapped_header in mapped_headers:
                if mapped_header in header_indices:
                    col_index = header_indices[mapped_header] + 1  # gspread columns are 1-indexed
                    data_column = matching_tab.col_values(col_index)[1:]  # Skip the header row
                    extracted_data.append((mapped_header, data_column))

            # Extract speed test data (assumes 'am', 'noon', and 'pm' are always in headers)
            speed_test_headers = ['am', 'noon', 'pm']
            for speed_header in speed_test_headers:
                if speed_header in header_indices:
                    col_index = header_indices[speed_header] + 1
                    speed_data = matching_tab.col_values(col_index)[1:]
                    extracted_data.append((speed_header, speed_data))
            
            return extracted_data
        else:
            st.write("No matching tab found for the provided URL.")
            return None
    else:
        st.write("No data available for the provided URL in the mapping sheet.")
        return None

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Get mapping and extract relevant data from the correct tab
    extracted_data = map_headers_and_extract_data(sheet1, url)
    
    if extracted_data:
        # Example chart data using extracted data (you can modify this based on real extracted values)
        labels = ["UK", "US", "Australia", "Italy", "Brazil"]
        datasets = [
            {
                "label": "NordVPN",
                "data": [51.49, 45.63, 40.91, 52.03, 37.15],  # Example data, replace with actual extracted data
                "backgroundColor": "rgba(62, 95, 255, 0.8)",
                "borderColor": "rgba(31, 47, 127, 0.8)",
                "borderWidth": 1
            },
            # Add other providers similarly with the real extracted data
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
