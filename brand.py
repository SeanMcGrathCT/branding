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

# Step 1: Convert the Google Sheet data to a pandas DataFrame
columns = consolidated_data[0]  # The first row is the header
rows = consolidated_data[1:]  # All other rows are data
sheet_data = pd.DataFrame(rows, columns=columns)

# Step 2: Handle 'Unnamed' and duplicate columns
def clean_column_names(columns):
    clean_columns = []
    seen = set()
    for i, col in enumerate(columns):
        if col == '' or col in seen:
            col = f"Column_{i+1}"  # Assign unique placeholder names to empty or duplicate columns
        clean_columns.append(col)
        seen.add(col)
    return clean_columns

# Clean the column names
sheet_data.columns = clean_column_names(sheet_data.columns)

# Step 3: Extract relevant columns for VPN providers, URLs, and speed tests
url_column = sheet_data.columns[0]  # URL column is the first one
vpn_column = sheet_data.columns[1]  # VPN provider names are in the second column

# Dynamically find columns related to speed tests and overall scores
speed_test_columns = [col for col in sheet_data.columns if 'Speed test' in col]
overall_score_columns = [col for col in sheet_data.columns if 'Overall Score' in col]

# Step 4: Create a new DataFrame with the relevant columns
provider_data = sheet_data[[url_column, vpn_column] + speed_test_columns + overall_score_columns]

# Step 5: Display the processed data
st.write("Processed Data (URLs, VPN Providers, Speed Tests, Overall Scores):")
st.write(provider_data.head())

# Now, you can proceed to generate charts, download the processed data, or any other operation.
