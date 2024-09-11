import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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
try:
    sheet1 = client.open_by_url(sheet1_url)
    sheet2 = client.open_by_url(sheet2_url)
    st.write("Successfully opened both Google Sheets.")
except Exception as e:
    st.error(f"Failed to open Google Sheets: {e}")

# List of ignored tabs
ignored_tabs = ['tables', 'Master', 'admin-prov-scores', 'admin-prov-scores_round', 'admin-global', 
                'Features Matrix', 'Index', 'Consolidated', 'Pages']

# Cache to store data from Sheet 1
cached_sheet_data = {}

# Function to load all worksheets into memory and cache them with detailed logging
def load_all_tabs_into_memory(sheet):
    st.write("Starting to load all tabs into memory...")
    for worksheet in sheet.worksheets():
        try:
            st.write(f"Processing worksheet: {worksheet.title}")
            if worksheet.title not in ignored_tabs:
                headers = worksheet.row_values(2)  # Load headers from row 2
                st.write(f"Headers from row 2 of {worksheet.title}: {headers}")
                
                # Check if the sheet has data
                if headers:
                    data = worksheet.get_all_values()[1:]  # Load data, skipping the first row (headers)
                    cached_sheet_data[worksheet.title] = {
                        'headers': headers,
                        'data': data
                    }
                    st.write(f"Successfully cached data from worksheet: {worksheet.title}")
                else:
                    st.write(f"No headers found in row 2 of {worksheet.title}. Skipping this sheet.")
            else:
                st.write(f"Skipping ignored tab: {worksheet.title}")
        except gspread.exceptions.APIError as api_error:
            st.error(f"APIError while processing worksheet {worksheet.title}: {api_error}")
        except Exception as e:
            st.error(f"An unexpected error occurred while processing worksheet {worksheet.title}: {e}")

# Load all data from sheet1 into cache
load_all_tabs_into_memory(sheet1)

# Function to find the correct tab based on the URL in cached data
def find_tab_in_cache_by_url(cached_data, url):
    st.write(f"Searching for URL {url} in cached data...")
    for tab_name, tab_data in cached_data.items():
        st.write(f"Checking tab: {tab_name}")
        try:
            if tab_data['data'] and tab_data['data'][0][0] == url:  # Assuming the URL is in the first cell of row 2 (A1)
                st.write(f"Found matching tab for URL {url}: {tab_name}")
                return tab_name, tab_data
        except Exception as e:
            st.error(f"Error while searching in tab {tab_name}: {e}")
    return None, None

# Function to map headers and find relevant data with logging
def map_headers_and_extract_data(url):
    try:
        st.write(f"Fetching mapping data for URL: {url}")
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
            
            # Find the correct worksheet in the cached data
            tab_name, matching_tab_data = find_tab_in_cache_by_url(cached_sheet_data, url)
            
            if matching_tab_data:
                st.write(f"Found matching tab: {tab_name}")
                
                # Get the headers and data from the cached tab data
                headers = matching_tab_data['headers']
                data = matching_tab_data['data']
                
                # Create a dictionary to map the Mapped Headers to their index positions
                header_indices = {header: index for index, header in enumerate(headers)}
                
                # Extract the data for the matched headers
                extracted_data = []
                for mapped_header in mapped_headers:
                    if mapped_header in header_indices:
                        col_index = header_indices[mapped_header]
                        data_column = [row[col_index] for row in data]
                        extracted_data.append((mapped_header, data_column))

                # Extract speed test data (assumes 'am', 'noon', and 'pm' are always in headers)
                speed_test_headers = ['am', 'noon', 'pm']
                for speed_header in speed_test_headers:
                    if speed_header in header_indices:
                        col_index = header_indices[speed_header]
                        speed_data = [row[col_index] for row in data]
                        extracted_data.append((speed_header, speed_data))
                
                return extracted_data
            else:
                st.write("No matching tab found for the provided URL.")
                return None
        else:
            st.write("No data available for the provided URL in the mapping sheet.")
            return None
    except gspread.exceptions.APIError as api_error:
        st.error(f"APIError while fetching mapping data for URL {url}: {api_error}")
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching mapping data for URL {url}: {e}")
    return None

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# User input for URL
url = st.text_input("Enter the URL to compare:")

if url:
    # Get mapping and extract relevant data from the correct tab
    extracted_data = map_headers_and_extract_data(url)
    
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
