import streamlit as st
import pandas as pd
import json

# Define VPN colors with less transparency for a more defined look
vpn_colors = {
    'nordvpn': 'rgba(62, 95, 255, 0.8)',
    'surfshark': 'rgba(30, 191, 191, 0.8)',
    'expressvpn': 'rgba(218, 57, 64, 0.8)',
    'ipvanish': 'rgba(112, 187, 68, 0.8)',
    'cyberghost': 'rgba(255, 204, 0, 0.8)',
    'purevpn': 'rgba(133, 102, 231, 0.8)',
    'protonvpn': 'rgba(109, 74, 255, 0.8)',
    'privatevpn': 'rgba(159, 97, 185, 0.8)',
    'pia': 'rgba(109, 200, 98, 0.8)',
    'hotspot shield': 'rgba(109, 192, 250, 0.8)',
    'strongvpn': 'rgba(238, 170, 29, 0.8)'
}

# Function to assign colors based on provider names
def get_color(provider_name):
    provider_name = provider_name.lower()
    return vpn_colors.get(provider_name, 'rgba(75, 192, 192, 0.8)')

# Streamlit UI
st.title("VPN Speed Comparison Chart Generator")

# Upload CSV file
uploaded_file = st.file_uploader("Choose a CSV file with source data", type="csv")
if uploaded_file is not None:
    source_data = pd.read_csv(uploaded_file)
    st.write("Data Preview:")
    st.dataframe(source_data)
    
    # Select the type of chart
    chart_type = st.selectbox("Select the type of chart:", ["Single Bar Chart", "Grouped Bar Chart"])
    
    # Select the columns for the chart
    if chart_type == "Single Bar Chart":
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns)
        value_column = st.selectbox("Select the column for speeds:", source_data.columns)
        mapped_columns = {label_column: value_column}
    else:
        label_column = st.selectbox("Select the column for VPN providers:", source_data.columns)
        value_columns = st.multiselect("Select the columns for tests:", source_data.columns)
        mapped_columns = {col: col for col in value_columns}
    
    # Input measurement unit
    measurement_unit = st.text_input("Enter the unit of measurement (e.g., Mbps):", "Mbps")
    
    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:")
    seo_description = st.text_area("Enter the SEO description for the chart:")

    # Select chart size
    chart_size = st.selectbox("Select the chart size:", ["Small", "Full Width"])
    if chart_size == "Small":
        chart_width = 500
        chart_height = 300
    else:
        chart_width = 805
        chart_height = 600
    
    if st.button("Generate HTML"):
        # Extract data for the chart
        labels = source_data[label_column].tolist()
        
        datasets = []
        if chart_type == "Single Bar Chart":
            values = source_data[mapped_columns[label_column]].tolist()
            colors = [get_color(provider) for provider in labels]
            datasets = [{
                'label': f'Speed ({measurement_unit})',
                'data': values,
                'backgroundColor': colors,
                'borderWidth': 1
            }]
        else:
            for col in mapped_columns.values():
                values = source_data[col].tolist()
                colors = [get_color(provider) for provider in labels]
                datasets.append({
                    'label': f'{col} ({measurement_unit})',
                    'data': values,
                    'backgroundColor': colors,
                    'borderColor': colors,
                    'borderWidth': 1
                })
        
        # Generate ld+json metadata
        metadata = {
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": seo_title,
            "description": seo_description,
            "data": {provider: {col: f"{source_data.loc[source_data[label_column] == provider, col].values[0]} {measurement_unit}" for col in mapped_columns.values()} for provider in labels}
        }

        # Generate the HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{seo_title}</title>
    <meta name="description" content="{seo_description}">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
    <script type="application/ld+json">
    {json.dumps(metadata, indent=4)}
    </script>
</head>
<body>
    <div style="width: 100%; max-width: {chart_width}px; margin: 0 auto;">
        <canvas id="vpnSpeedChart" width="{chart_width}" height="{chart_height}"></canvas>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var ctx = document.getElementById('vpnSpeedChart').getContext('2d');
            var vpnSpeedChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: {json.dumps(datasets)}
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'VPN Speed Comparison ({measurement_unit})',
                            font: {{
                                size: 18
                            }}
                        }},
                        legend: {{
                            display: true
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.raw + ' {measurement_unit}';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Speed ({measurement_unit})'
                            }}
                        }}
                    }}
                }}
            }});
        }});
    </script>
</body>
</html>
"""
        # Display download button for the HTML content
        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )

# Ensure to include logging for each step
st.write("Log:")
