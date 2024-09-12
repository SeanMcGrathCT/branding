import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import numpy as np

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

# Step 1: Check for problematic data types and null values
st.write("Shape of the DataFrame:", sheet_data.shape)

# Show raw data preview (no conversion to Arrow yet)
st.write("First 10 rows of raw data:")
st.write(sheet_data.head(10))  # Using st.write() instead of st.dataframe()

# Check column data types
st.write("Column Data Types:")
st.write(sheet_data.dtypes)

# Show any potential null or missing values in the dataset
st.write("Missing values in data:")
st.write(sheet_data.isnull().sum())

# Step 2: Convert all columns to string to avoid mixed data type issues
sheet_data = sheet_data.applymap(str)

# Step 3: Display first 10 rows after type coercion to string
st.write("First 10 rows after converting all columns to strings:")
try:
    st.dataframe(sheet_data.head(10))
except ValueError as e:
    st.error(f"Error displaying DataFrame: {e}")

# Step 4: Filter out any problematic columns (example based on issues identified in previous step)
# Here you would identify and add any problematic columns to the list below based on your findings
problematic_columns = []  # Add problematic columns if needed

# Filter out those columns
if problematic_columns:
    filtered_data = sheet_data.drop(columns=problematic_columns)
    st.write(f"Filtered Data (excluding columns {problematic_columns}):")
    st.dataframe(filtered_data.head(10))
else:
    st.write("No problematic columns identified.")

# Step 5: Debugging: If the issue persists, check for object-like cells in columns
for column in sheet_data.columns:
    if sheet_data[column].apply(lambda x: isinstance(x, object)).any():
        st.write(f"Column '{column}' contains object-like data that could cause issues.")

# Step 6: Test with a subset of columns (first 10 columns) to isolate issues
subset_columns = sheet_data.columns[:10]
subset_data = sheet_data[subset_columns]

st.write("Subset of data (first 10 columns):")
try:
    st.dataframe(subset_data.head(10))
except ValueError as e:
    st.error(f"Error displaying subset DataFrame: {e}")
