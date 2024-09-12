import streamlit as st
import pandas as pd

# Load the CSV file provided by the user
file_path = '/mnt/data/VPN Master - page level scoring - Consolidated (2).csv'
sheet_data = pd.read_csv(file_path)

# Display the raw data structure for reference
st.write("Raw Data Structure:")
st.write(sheet_data.head())

# Step 1: Rename columns where possible based on the first row
# The first row contains actual headers for the sheet
headers = sheet_data.iloc[0]  # First row as column headers

# Assign new headers to the DataFrame and drop the first row
sheet_data.columns = headers
sheet_data = sheet_data.drop(0)

# Step 2: Display the cleaned data with new headers
st.write("Data after header adjustment:")
st.write(sheet_data.head())

# Step 3: Extract relevant columns
# Identify key columns: URLs, VPN providers, and overall scores

# URLs are in the first column, and VPN providers are in the second column
url_column = sheet_data.columns[0]
vpn_column = sheet_data.columns[1]

# Find all columns containing speed test or overall score data
speed_test_columns = [col for col in sheet_data.columns if 'Speed test' in str(col)]
overall_score_columns = [col for col in sheet_data.columns if 'Overall Score' in str(col)]

# Display the relevant columns to ensure correctness
st.write("Relevant Columns for Analysis:")
st.write(f"URL Column: {url_column}")
st.write(f"VPN Provider Column: {vpn_column}")
st.write(f"Speed Test Columns: {speed_test_columns}")
st.write(f"Overall Score Columns: {overall_score_columns}")

# Step 4: Process the speed test and overall score data for each VPN provider
# Extract the required data into a new DataFrame for further analysis or charting
provider_data = sheet_data[[url_column, vpn_column] + speed_test_columns + overall_score_columns]

# Display the processed data
st.write("Processed Data (URLs, VPN Providers, Speed Tests, Overall Scores):")
st.write(provider_data.head())

# Step 5: Further actions can include generating charts or exporting the data
