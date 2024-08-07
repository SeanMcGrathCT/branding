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
creds = ServiceAccountCredentials.from_json_keyfile_name('gsheet.json', scope)
client = gspread.authorize(creds)

# Load the Google Sheets document by URL
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q/edit?usp=sharing'
spreadsheet = client.open_by_url(spreadsheet_url)

# Load the sheets into dataframes
articles_df = pd.DataFrame(spreadsheet.worksheet('Master').get_all_records())
consolidated_df = pd.DataFrame(spreadsheet.worksheet('Consolidated').get_all_records())

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
    other_cols = [col for col in cols not in sitewide_testing_columns and col != 'Provider']
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
    with open('mappings.json', 'w') as file:
        json.dump(mappings, file)

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
        st.success("Mappings saved successfully")
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

# Initialize variables for form fields
seo_title = ""
seo_description = ""
label_column = ""
value_columns = []
measurement_unit = "Mbps"
empty_bar_text = "No data available"
chart_size = "Full Width"
chart_width = 805
chart_height = 600
grouping_method = "Provider"
display_legend = True
source_data = None

if action == "Create New Chart":
    # Upload CSV file
    uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
    if uploaded_file is not None:
        source_data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        source_data = st.data_editor(source_data)
elif action == "Update Existing Chart":
    chart_html = st.text_area("Paste the HTML content of the existing chart:")
    if chart_html:
        chart_data = load_chart_data_from_html(chart_html)
        if chart_data:
            labels = list(chart_data["data"].values())[0].keys()
            datasets = [{"label": k, "data": list(v.values())} for k, v in chart_data["data"].items()]
            seo_title = chart_data.get("name", "")
            seo_description = chart_data.get("description", "")
            measurement_unit = "Mbps"  # Assuming the unit is always Mbps
            empty_bar_text = "No data available"
            display_legend = True
            grouping_method = "Provider"
            chart_size = "Full Width"
            chart_width = 805
            chart_height = 600
            # Reconstruct the source_data dataframe from the datasets
            label_column = "VPN provider"
            data_dict = {label_column: labels}
            for dataset in datasets:
                data_dict[dataset["label"]] = dataset["data"]
            source_data = pd.DataFrame(data_dict)
            st.write("Data Preview:")
            source_data = st.data_editor(source_data)
elif action == "Check URL":
    url = st.text_input("Enter the URL of the page:")
    if url:
        scraped_scores = scrape_scores_from_url(url)
        st.write(f"Scraped Scores: {scraped_scores}")

        filtered_data = consolidated_df[consolidated_df['Article URL'].str.contains(url, case=False, na=False)]
        st.write(f"Filtered data: {filtered_data}")

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
                    if st.button("Create Graph", key=f"{parent_category}_graph"):
                        source_data = pivoted_data  # Use this data for chart creation below
                except ValueError as e:
                    st.write(f"Error processing category {parent_category}: {e}")
        else:
            st.write("No data found for the specified URL.")

if source_data is not None:
    # Select the type of chart
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart", "Scatter Chart", "Radar Chart"])

    # Select the columns for the chart
    if not source_data.empty:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns, key='label_column')
        # Ensure the default value columns are valid columns in the dataframe
        valid_columns = list(source_data.columns)
        default_columns = valid_columns[1:] if len(valid_columns) > 1 else valid_columns
        if chart_type == "Scatter Chart":
            x_column = st.selectbox("Select the column for X-axis values:", valid_columns, key='x_column')
            y_column = st.selectbox("Select the column for Y-axis values:", valid_columns, key='y_column')
        else:
            value_columns = st.multiselect("Select the columns for tests:", valid_columns, default=default_columns, key='value_columns')

    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:", seo_title)
    seo_description = st.text_area("Enter the SEO description for the chart:", seo_description)

    if chart_type != "Scatter Chart":
        # Input Y axis label
        y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")

    # Input measurement unit
    measurement_unit = st.text_input("Enter the measurement unit:", measurement_unit)

    # Input text for empty bar tooltip
    empty_bar_text = st.text_input("Enter the text for empty bar tooltips:", empty_bar_text)

    # Select chart size
    chart_size = st.selectbox("Select the chart size:", ["Full Width", "Medium", "Small"])
    if chart_size == "Full Width":
        chart_width = 805
        chart_height = 600
    elif chart_size == "Medium":
        chart_width = 605
        chart_height = 500
    else:
        chart_width = 405
        chart_height = 400

    # Grouping method for bar charts
    if chart_type == "Grouped Bar Chart":
        grouping_method = st.selectbox("Group by Provider or Test Type:", ["Provider", "Test Type"], key='grouping_method')
    else:
        grouping_method = "Provider"

    # Display legend
    display_legend = st.checkbox("Display legend", value=display_legend)

    if st.button("Generate HTML"):
        datasets = []
        null_value = 0.05  # Small fixed value for null entries
        if chart_type == "Scatter Chart":
            labels = []
            x_values = []
            y_values = []
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                try:
                    x_val = float(provider_data[x_column].values[0])
                    y_val = float(provider_data[y_column].values[0])
                    x_values.append(x_val)
                    y_values.append(y_val)
                    scatter_data = [{'x': x_val, 'y': y_val}]
                    background_colors = [get_provider_color(provider)]
                    border_colors = background_colors
                    datasets.append({
                        'label': provider,
                        'data': scatter_data,
                        'backgroundColor': background_colors,
                        'borderColor': border_colors,
                        'borderWidth': 1,
                        'showLine': False
                    })
                except ValueError as e:
                    st.error(f"Error converting values to float for provider '{provider}': {e}")
                    continue
            if x_values and y_values:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)
        elif chart_type == "Radar Chart":
            labels = value_columns
            for provider in source_data[label_column].unique():
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0].split(' ')[0]) if isinstance(provider_data[col].values[0], str) else provider_data[col].values[0]
                    for col in value_columns
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = get_provider_color(provider)
                border_colors = background_colors
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
        elif grouping_method == "Provider":
            labels = list(value_columns)
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    float(provider_data[col].values[0].split(' ')[0]) if isinstance(provider_data[col].values[0], str) else provider_data[col].values[0]
                    for col in value_columns
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = [
                    get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)'
                    for col in value_columns
                ]
                border_colors = background_colors
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
        else:  # Group by Test Type
            labels = source_data[label_column].tolist()
            color_index = 0
            for col in value_columns:
                values = [
                    float(value.split(' ')[0]) if isinstance(value, str) and ' ' in value else value
                    for value in source_data[col].tolist()
                    if pd.api.types.is_numeric_dtype(source_data[col])
                ]
                background_colors = [
                    nice_colors[color_index % len(nice_colors)] if not pd.isna(value) else 'rgba(169, 169, 169, 0.8)'
                    for value in values
                ]
                border_colors = background_colors
                datasets.append({
                    'label': col,
                    'data': values,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
                color_index += 1

        # Generate ld+json metadata
        if chart_type == "Scatter Chart":
            data_dict = {provider: {x_column: provider_data[x_column].tolist(), y_column: provider_data[y_column].tolist()} for provider in source_data[label_column].unique()}
        elif chart_type == "Radar Chart":
            data_dict = {provider: {col: f"{provider_data.at[provider_data.index[0], col]} {measurement_unit}".split(' ')[0] + ' ' + measurement_unit for col in value_columns} for provider, provider_data in source_data.groupby(label_column)}
        else:
            data_dict = {provider: {col: f"{source_data.at[source_data[source_data[label_column] == provider].index[0], col]} {measurement_unit}".split(' ')[0] + ' ' + measurement_unit for col in value_columns} for provider in source_data[label_column]}
        
        metadata = {
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": seo_title,
            "description": seo_description,
            "data": data_dict
        }

        # Generate the HTML content for insertion
        unique_id = generate_unique_id(seo_title)
        html_content = f"""
<div id="{unique_id}" style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart_{unique_id}" width="{chart_width}" height="{chart_height}"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('vpnSpeedChart_{unique_id}').getContext('2d');
        
        var vpnSpeedChart = new Chart(ctx, {{
            type: '{'radar' if chart_type == 'Radar Chart' else 'scatter' if chart_type == 'Scatter Chart' else 'bar'}',
            data: {{
                labels: {json.dumps(labels)},
                datasets: {json.dumps(datasets, default=str)}
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: '{seo_title}',
                        font: {{
                            size: 18
                        }}
                    }},
                    legend: {{
                        display: {str(display_legend).lower()}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                if (context.raw <= {null_value * 1.1}) {{
                                    return '{empty_bar_text}';
                                }}
                                if (context.raw && context.raw.x !== undefined && context.raw.y !== undefined) {{
                                    return context.dataset.label + ': (' + context.raw.x + ', ' + context.raw.y + ')';
                                }}
                                return context.dataset.label + ': ' + context.raw + ' {measurement_unit}';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: {str(chart_type != 'Radar Chart').lower()},
                        min: {(x_min - 1) if chart_type == 'Scatter Chart' else 'null'},
                        max: {(x_max + 1) if chart_type == 'Scatter Chart' else 'null'},
                        title: {{
                            display: true,
                            text: '{x_column if chart_type == 'Scatter Chart' else ''}'
                        }}
                    }},
                    y: {{
                        beginAtZero: {str(chart_type != 'Radar Chart').lower()},
                        min: {(y_min - 5) if chart_type == 'Scatter Chart' else 'null'},
                        max: {(y_max + 5) if chart_type == 'Scatter Chart' else 'null'},
                        title: {{
                            display: true,
                            text: '{y_column if chart_type == 'Scatter Chart' else y_axis_label}'
                        }}
                    }}
                }}
            }}
        }});
    }});
</script>
<script type="application/ld+json">
{json.dumps(metadata, indent=4)}
</script>
"""

        # Save the HTML content to a file
        html_file_path = f"{unique_id}.html"
        with open(html_file_path, "w") as html_file:
            html_file.write(html_content)

        # Upload the file to Firebase Storage
        bucket = storage.bucket()
        public_url = upload_to_firebase_storage(html_file_path, bucket, f"charts/{unique_id}.html")

        # Log the upload to Google Sheets
        google_credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["GCP_SERVICE_ACCOUNT"])
        )
        service = build('sheets', 'v4', credentials=google_credentials)
        sheet = service.spreadsheets()

        # Prepare the data to be logged
        log_data = [
            unique_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            seo_title,
            seo_description,
            public_url
        ]

        # Append the data to the Google Sheets
        sheet.values().append(
            spreadsheetId="1ZhJhTJSzrdM2c7EoWioMkzWpONJNyalFmWQDSue577Q",
            range="charts!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": [log_data]}
        ).execute()

        # Display download button for the HTML content
        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )

        # Provide the public URL of the uploaded chart
        st.write(f"Chart has been uploaded to Firebase. [View Chart]({public_url})")

# Ensure to include logging for each step
st.write("Log:")
