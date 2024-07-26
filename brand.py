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
    label_column = st.selectbox("Select the column for VPN providers:", source_data.columns)
    value_columns = st.multiselect("Select the columns for tests:", source_data.columns)
    mapped_columns = {col: col for col in value_columns}
    
    # Input measurement unit
    measurement_unit = st.text_input("Enter the unit of measurement (e.g., Mbps):", "Mbps")
    
    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:")
    seo_description = st.text_area("Enter the SEO description for the chart:")

    # Input Y axis label
    y_axis_label = st.text_input("Enter the Y axis label:", "Speed (Mbps)")

    # Input text for empty bars
    empty_bar_text = st.text_input("Enter text for empty bars (e.g., 'No servers in Egypt'):", "No data available")

    # Select chart size
    chart_size = st.selectbox("Select the chart size:", ["Small", "Full Width"])
    if chart_size == "Small":
        chart_width = 500
        chart_height = 300
    else:
        chart_width = 805
        chart_height = 600
    
    # Select grouping method
    grouping_method = st.selectbox("Group data by:", ["Provider", "Test Type"])
    
    # Select whether to display the legend
    display_legend = st.checkbox("Display legend", value=True)
    
    if st.button("Generate HTML"):
        datasets = []
        if grouping_method == "Provider":
            labels = list(mapped_columns.keys())
            unique_providers = source_data[label_column].unique()
            for provider in unique_providers:
                provider_data = source_data[source_data[label_column] == provider]
                data = [
                    provider_data[col].values[0] if not pd.isna(provider_data[col].values[0]) else None
                    for col in mapped_columns.values()
                ]
                background_colors = [
                    get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)'
                    for col in mapped_columns.values()
                ]
                border_colors = [
                    get_provider_color(provider) if not pd.isna(provider_data[col].values[0]) else 'rgba(169, 169, 169, 0.8)'
                    for col in mapped_columns.values()
                ]
                datasets.append({
                    'label': provider,
                    'data': data,
                    'backgroundColor': background_colors,
                    'borderColor': border_colors,
                    'borderWidth': 1
                })
        else:  # Group by Test Type
            labels = source_data[label_column].tolist()
            for i, col in enumerate(mapped_columns.values()):
                values = [
                    value if not pd.isna(value) else None
                    for value in source_data[col].tolist()
                ]
                background_colors = [
                    nice_colors[i % len(nice_colors)] if value is not None else 'rgba(169, 169, 169, 0.8)'
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
        
        # Generate ld+json metadata
        metadata = {
            "@context": "http://schema.org",
            "@type": "Dataset",
            "name": seo_title,
            "description": seo_description,
            "data": {provider: {col: f"{source_data.loc[source_data[label_column] == provider, col].values[0]} {measurement_unit}" for col in mapped_columns.values()} for provider in source_data[label_column].unique()}
        }

        # Generate the HTML content for insertion
        html_content = f"""
<div style="max-width: {chart_width}px; margin: 0 auto;">
    <canvas class="jschartgraphic" id="vpnSpeedChart" width="{chart_width}" height="{chart_height}"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.7.0/chart.min.js"></script>
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
                                if (context.raw === null) {{
                                    return '{empty_bar_text}';
                                }}
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
                            text: '{y_axis_label}'
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
        # Display download button for the HTML content
        st.download_button(
            label="Download HTML",
            data=html_content,
            file_name="vpn_speed_comparison.html",
            mime="text/html"
        )

# Ensure to include logging for each step
st.write("Log:")
