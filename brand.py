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

# Convert the data to a pandas DataFrame
columns = consolidated_data[0]  # Headers
rows = consolidated_data[1:]  # Data rows

# Basic check: How many rows and columns do we have?
st.write(f"Loaded {len(rows)} rows and {len(columns)} columns from the sheet.")

# Step 1: Basic row-by-row check for problematic data
# This will print any rows that have potential issues when converting to a DataFrame
clean_rows = []
problematic_rows = []

for i, row in enumerate(rows):
    try:
        clean_rows.append([str(item) for item in row])  # Convert everything to string
    except Exception as e:
        problematic_rows.append((i, row, str(e)))

# If we found problematic rows, display them
if problematic_rows:
    st.write("Found problematic rows:")
    st.write(problematic_rows)
else:
    st.write("No problematic rows found. Proceeding with data conversion.")

# Now that we've cleaned the rows, create a DataFrame
sheet_data = pd.DataFrame(clean_rows, columns=columns)

# Step 2: Display the first 10 rows to ensure it’s loading properly
try:
    st.write("First 10 rows of data:")
    st.write(sheet_data.head(10))  # Display raw data as a table (not Arrow)
except Exception as e:
    st.error(f"Error displaying DataFrame: {e}")

# Step 3: Convert columns to string types to ensure compatibility
sheet_data = sheet_data.astype(str)

# Step 4: Check for object-like columns or problematic columns
problematic_columns = []
for column in sheet_data.columns:
    if sheet_data[column].apply(lambda x: isinstance(x, object)).any():
        problematic_columns.append(column)
        st.write(f"Column '{column}' contains object-like data.")

# If problematic columns are found, display a message
if problematic_columns:
    st.write(f"These columns may have caused issues: {problematic_columns}")
else:
    st.write("No problematic columns found.")

# Step 5: Display the shape and columns
st.write("Final DataFrame Shape:", sheet_data.shape)
st.write("Columns:", sheet_data.columns.tolist())
