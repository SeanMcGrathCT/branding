import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import uuid
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define VPN colors with less transparency for a more defined look
vpn_colors = {
    'nordvpn': 'rgba(62, 95, 255, 0.8)',
    'surfshark': 'rgba(30, 191, 191, 0.8)',
    'expressvpn': 'rgba(218, 57, 64, 0.8)',
    'ipvanish': 'rgba(112, 187, 68, 0.8)',
    'cyberghost': 'rgba(255, 204, 0.8)',
    'purevpn': 'rgba(133, 102, 231, 0.8)',
    'protonvpn': 'rgba(109, 74, 255, 0.8)',
    'privatevpn': 'rgba(159, 97, 185, 0.8)',
    'pia': 'rgba(109, 200, 98, 0.8)',
    'hotspot shield': 'rgba(109, 192, 250, 0.8)',
    'strongvpn': 'rgba(238, 170, 29, 0.8)'
}

# Define nice colors for test types
nice_colors = [
    'rgba(255, 99, 132, 0.8)',
    'rgba(54, 162, 235, 0.8)',
    'rgba(255, 206, 86, 0.8)',
    'rgba(75, 192, 192, 0.8)',
    'rgba(153, 102, 255, 0.8)',
    'rgba(255, 159, 64, 0.8)'
]

# Function to assign colors based on provider names
def get_provider_color(provider_name):
    if isinstance(provider_name, str):
        provider_name = provider_name.lower()
        return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')
    return 'rgba(75, 192, 192, 0.8)'

def generate_unique_id(title):
    unique_id = title.replace(" ", "_").lower() + "_" + uuid.uuid4().hex[:6]
    return unique_id

# Streamlit UI
st.title("VPN Data and Chart Tool")

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    firebase_credentials = dict(st.secrets["FIREBASE_CREDENTIALS"])
    # Convert the string private key into the required format
    firebase_credentials['private_key'] = firebase_credentials['private_key'].replace('\\n', '\n')
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'storageBucket': f"{firebase_credentials['project_id']}.appspot.com"
    })

def upload_to_firebase_storage(file_path, bucket, destination_blob_name):
    """Uploads a file to the bucket."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return blob.public_url

def load_chart_data_from_html(html_content):
    try:
        # Locate the start and end of the JSON data within the script
        start_marker = '<script type="application/ld+json">'
        end_marker = '</script>'
        
        start = html_content.find(start_marker)
        end = html_content.find(end_marker, start)

        if start == -1 or end == -1:
            raise ValueError("Could not find the JSON data section in the provided HTML content.")
        
        # Extract and clean the JSON data
        json_data = html_content[start+len(start_marker):end].strip()
        
        data = json.loads(json_data)
        return data
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON data from HTML content: {e}")
        return None
    except ValueError as e:
        st.error(e)
        return None

# Google Sheets authorization
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["GCP_SERVICE_ACCOUNT"], scope)
client = gspread.authorize(creds)

# Load the Google Sheets document by URL
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q/edit?usp=sharing'

try:
    spreadsheet = client.open_by_url(spreadsheet_url)
    articles_df = pd.DataFrame(spreadsheet.worksheet('Master').get_all_records())
    consolidated_df = pd.DataFrame(spreadsheet.worksheet('Consolidated').get_all_records())
except APIError as e:
    st.error(f"An error occurred while accessing the Google Sheets API: {e}")
    st.stop()

# Radio button for creating, updating chart, or checking URL
action = st.radio("Choose an action:", ["Create New Chart", "Update Existing Chart", "Check URL"], key='action_choice')

def pivot_data(data):
    data = data.drop_duplicates(subset=['Provider', 'Data Point Name'])
    pivoted_data = data.pivot(index='Provider', columns='Data Point Name', values='Data Point Value').reset_index()
    pivoted_data = pivoted_data.applymap(lambda x: '{:.2f}'.format(x) if isinstance(x, (int, float)) else x)
    return pivoted_data

def move_sitewide_testing_columns(df, sitewide_testing_columns):
    cols = df.columns.tolist()
    provider_col = ['Provider']
    sitewide_cols = [col for col in cols if col in sitewide_testing_columns]
    other_cols = [col for col in cols if col not in sitewide_testing_columns and col != 'Provider']
    return df[provider_col + sitewide_cols + other_cols]

def move_overall_score_to_end(df):
    cols = df.columns.tolist()
    overall_cols = [col for col in cols if 'overall score' in col.lower() and col != 'Overall score out of 10']
    other_cols = [col for col in cols if 'overall score' not in col.lower()]
    return df[other_cols + overall_cols + ['Overall score out of 10']] if 'Overall score out of 10' in cols else df[other_cols + overall_cols]

def sort_by_overall_score(df):
    overall_score_col = df.columns[-1]
    df[overall_score_col] = pd.to_numeric(df[overall_score_col], errors='coerce')
    return df.sort_values(by=overall_score_col, ascending=False)

def create_overall_scores_table(data):
    overall_scores = data[data['Data Point Name'].str.contains('overall score', case=False, na=False)]
    if not overall_scores.empty:
        overall_scores = overall_scores.drop_duplicates(subset=['Provider', 'Data Point Name'])
        overall_scores_pivoted = overall_scores.pivot(index='Provider', columns='Data Point Name', values='Data Point Value').reset_index()
        overall_scores_pivoted = overall_scores_pivoted.applymap(lambda x: '{:.2f}'.format(x) if isinstance(x, (int, float)) else x)
        overall_scores_pivoted = sort_by_overall_score(overall_scores_pivoted)
        return overall_scores_pivoted
    return pd.DataFrame()

def highlight_sitewide_testing(df, sitewide_testing_columns):
    def highlight_cols(val):
        color = 'background-color: #9370DB'
        return [color if col in sitewide_testing_columns else '' for col in df.columns]
    return df.style.apply(highlight_cols, axis=1)

def scrape_scores_from_url(url):
    st.write(f"Scraping URL: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers)
        st.write(f"Response status code: {response.status_code}")
        if response.status_code != 200:
            st.error("Error fetching the URL")
            return {}

        soup = BeautifulSoup(response.content, 'html.parser')
        scores = {}
        current_provider = None
        for element in soup.find_all(['h2', 'h3', 'div']):
            if element.name in ['h2', 'h3'] and element.find('a'):
                current_provider = element.get_text(strip=True)
                current_provider = current_provider.split('. ', 1)[-1]  # Remove the numbering
            if element.name == 'div' and 'scores' in element.get('class', []):
                score_table = element.find('table', class_='provider-scores')
                if score_table and current_provider:
                    rows = score_table.find_all('tr')
                    provider_scores = {}
                    for row in rows:
                        th = row.find('th').get_text(strip=True).replace(':', '')
                        td = row.find('td').find('strong').get_text(strip=True).split(' ')[0]  # Get the score before the "/"
                        provider_scores[th] = td
                    scores[current_provider] = provider_scores

        st.write(f"Scraped scores: {scores}")
        if not scores:
            st.error("No scores found on the page. Please check the structure of the HTML.")
        return scores
    except Exception as e:
        st.error(f"Exception occurred while scraping: {e}")
        return {}

def load_mappings():
    try:
        with open('mappings.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_mappings(mappings):
    try:
        with open('mappings.json', 'w') as file:
            json.dump(mappings, file)
        st.success("Mappings saved successfully")
    except Exception as e:
        st.error(f"Failed to save mappings: {e}")

def create_mapping_ui(scraped_scores, google_sheets_scores):
    mappings = load_mappings()
    new_mappings = {}
    all_scores = {score_name for scores in scraped_scores.values() for score_name in scores}

    for score_name in all_scores:
        if score_name not in mappings:
            selected_google_sheet_score = st.selectbox(f"Map '{score_name}' to Google Sheets score:", google_sheets_scores, key=f"{score_name}")
            new_mappings[score_name] = selected_google_sheet_score

    if st.button("Save Mappings"):
        mappings.update(new_mappings)
        save_mappings(mappings)
        st.experimental_rerun()  # Rerun the script to apply new mappings

def edit_mapping_ui(scraped_scores, google_sheets_scores):
    mappings = load_mappings()
    all_scores = {score_name for scores in scraped_scores.values() for score_name in scores}

    for score_name in all_scores:
        selected_google_sheet_score = st.selectbox(f"Edit mapping for '{score_name}' (currently mapped to '{mappings.get(score_name, 'None')}'):", google_sheets_scores, key=f"edit_{score_name}")
        mappings[score_name] = selected_google_sheet_score

    if st.button("Save Edited Mappings"):
        save_mappings(mappings)
        st.success("Edited mappings saved successfully")
        st.experimental_rerun()  # Rerun the script to apply new mappings

def compare_scores(scraped_scores, filtered_data):
    mappings = load_mappings()
    mismatches = {}

    for provider, scores in scraped_scores.items():
        provider_data = filtered_data[filtered_data['Provider'] == provider]
        if not provider_data.empty:
            for score_name, scraped_score in scores.items():
                mapped_name = mappings.get(score_name)
                if mapped_name:
                    gs_score = provider_data[provider_data['Data Point Name'] == mapped_name]['Data Point Value']
                    if not gs_score.empty:
                        gs_score_value = gs_score.values[0]
                        try:
                            if float(scraped_score) != float(gs_score_value):
                                mismatches[provider] = mismatches.get(provider, [])
                                mismatches[provider].append((score_name, scraped_score, gs_score_value))
                        except ValueError:
                            st.error(f"Non-numeric value encountered: Scraped score: {scraped_score}, Google Sheets score: {gs_score_value} for {provider} - {score_name}")
                            mismatches[provider] = mismatches.get(provider, [])
                            mismatches[provider].append((score_name, scraped_score, gs_score_value))
    return mismatches

if action == "Check URL":
    url = st.text_input("Enter the URL of the page:")
    if url:
        scraped_scores = scrape_scores_from_url(url)
        st.write(f"Scraped Scores: {scraped_scores}")

        filtered_data = consolidated_df[consolidated_df['Article URL'].str.contains(url, case=False, na=False)]
        
        # Debug statement to ensure filtered_data is correct
        st.write("Filtered data preview:", filtered_data.head())
        st.write("Columns in filtered_data:", filtered_data.columns.tolist())

        if 'Parent Category' not in filtered_data.columns or 'Data Point Name' not in filtered_data.columns:
            st.error("Required columns are missing in the filtered data.")
            st.stop()

        sitewide_testing_columns = filtered_data[filtered_data['Parent Category'].str.contains('sitewide testing', case=False, na=False)]['Data Point Name'].unique()
        st.write(f"Sitewide testing columns: {sitewide_testing_columns}")

        if not filtered_data.empty:
            google_sheets_scores = filtered_data['Data Point Name'].unique().tolist()
            if scraped_scores:
                # Load mappings and check if they are complete
                mappings = load_mappings()
                missing_mappings = [score for score in {score_name for scores in scraped_scores.values() for score_name in scores} if score not in mappings]

                if missing_mappings:
                    create_mapping_ui(scraped_scores, google_sheets_scores)
                    st.warning("Please complete the mappings and click 'Save Mappings' to continue.")
                else:
                    mismatches = compare_scores(scraped_scores, filtered_data)
                    if mismatches:
                        st.write("### Mismatched Scores")
                        for provider, mismatch_list in mismatches.items():
                            st.write(f"#### {provider}")
                            for score_name, scraped_score, gs_score in mismatch_list:
                                st.write(f"**{score_name}**: Scraped: {scraped_score}, Google Sheets: {gs_score}")
                    else:
                        st.write("All scores match between the scraped data and Google Sheets.")

                    # Provide an option to edit the mapping
                    if st.button("Edit Mappings"):
                        edit_mapping_ui(scraped_scores, google_sheets_scores)

            overall_scores_table = create_overall_scores_table(filtered_data)
            if not overall_scores_table.empty:
                st.write("#### Overall Scores")
                overall_scores_table = move_overall_score_to_end(overall_scores_table)
                overall_scores_table = move_sitewide_testing_columns(overall_scores_table, sitewide_testing_columns)
                styled_overall_scores_table = highlight_sitewide_testing(overall_scores_table, sitewide_testing_columns)
                st.dataframe(styled_overall_scores_table)
                csv_data = overall_scores_table.to_csv(index=False)
                st.download_button(
                    label="Export Overall Scores to CSV",
                    data=csv_data,
                    file_name=f"Overall_Scores.csv",
                    mime='text/csv'
                )

            st.write(f"Data for {url}:")
            for parent_category in filtered_data['Parent Category'].unique():
                st.write(f"#### {parent_category}")
                category_data = filtered_data[filtered_data['Parent Category'] == parent_category]
                try:
                    pivoted_data = pivot_data(category_data)
                    pivoted_data = move_overall_score_to_end(pivoted_data)
                    pivoted_data = pivoted_data.applymap(lambda x: '{:.2f}'.format(x) if isinstance(x, (int, float)) else x)
                    pivoted_data = sort_by_overall_score(pivoted_data)
                    st.dataframe(pivoted_data)
                    csv_data = pivoted_data.to_csv(index=False)
                    st.download_button(
                        label=f"Export {parent_category} data to CSV",
                        data=csv_data,
                        file_name=f"{parent_category}.csv",
                        mime='text/csv'
                    )
                except ValueError as e:
                    st.write(f"Error processing category {parent_category}: {e}")
        else:
            st.write("No data found for the specified URL.")
