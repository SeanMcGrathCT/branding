import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

# Step 1: Set up Google Sheets access
credentials_info = st.secrets["gsheet_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize client
client = gspread.authorize(creds)

# Load the Google Sheet
sheet1_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q'
sheet1 = client.open_by_url(sheet1_url)
consolidated_sheet = sheet1.worksheet('Consolidated')
consolidated_data = consolidated_sheet.get_all_values()

# Convert the sheet data to a DataFrame
columns = consolidated_data[0]  # Header row
rows = consolidated_data[1:]  # Data rows
sheet_data = pd.DataFrame(rows, columns=columns)

# Clean column names (handle empty or duplicate columns)
def clean_column_names(columns):
    clean_columns = []
    seen = set()
    for i, col in enumerate(columns):
        if col == '' or col in seen:
            col = f"Column_{i+1}"  # Assign unique placeholder names to empty or duplicate columns
        clean_columns.append(col)
        seen.add(col)
    return clean_columns

sheet_data.columns = clean_column_names(sheet_data.columns)

# Step 2: Prompt the user for a URL
st.write("Enter the URL to find the corresponding VPN data:")
input_url = st.text_input("URL", "")

# Step 3: Search for the URL in the dataset
if input_url:
    matching_rows = sheet_data[sheet_data[sheet_data.columns[0]] == input_url]

    if not matching_rows.empty:
        st.write(f"Data found for URL: {input_url}")
        
        # Extract VPN provider and test results
        vpn_column = matching_rows[sheet_data.columns[1]].values[0]
        st.write(f"VPN Provider: {vpn_column}")
        
        # Step 4: Find speed test and overall score columns
        speed_test_columns = [col for col in sheet_data.columns if 'Speed test' in col]
        overall_score_columns = [col for col in sheet_data.columns if 'Overall Score' in col]

        # Extract speed test data
        speed_test_data = matching_rows[speed_test_columns].astype(float)
        overall_score_data = matching_rows[overall_score_columns].astype(float)

        st.write("Speed Test Data:")
        st.write(speed_test_data)

        st.write("Overall Score Data:")
        st.write(overall_score_data)

        # Step 5: Generate Charts

        # Speed Test Chart
        fig, ax = plt.subplots()
        ax.bar(speed_test_columns, speed_test_data.values.flatten(), color='skyblue')
        ax.set_title(f"{vpn_column} - Speed Test Results")
        ax.set_xlabel("Region")
        ax.set_ylabel("Speed (Mbps)")
        st.pyplot(fig)

        # Overall Score Chart
        fig, ax = plt.subplots()
        ax.bar(overall_score_columns, overall_score_data.values.flatten(), color='lightcoral')
        ax.set_title(f"{vpn_column} - Overall Scores")
        ax.set_xlabel("Metric")
        ax.set_ylabel("Score")
        st.pyplot(fig)

    else:
        st.write(f"No data found for URL: {input_url}")

