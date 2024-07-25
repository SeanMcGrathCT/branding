import streamlit as st
import pandas as pd
import json

# Define VPN colors with gradients for a modern look
vpn_colors = {
    'nordvpn': ('#3e5fff', '#1e3a8a'),
    'surfshark': ('#1EBFBF', '#0f7978'),
    'expressvpn': ('#DA3940', '#7a191d'),
    'ipvanish': ('#70BB44', '#426b2d'),
    'cyberghost': ('#FFCC00', '#b38600'),
    'purevpn': ('#8566E7', '#483194'),
    'protonvpn': ('#6D4AFF', '#3a1c8a'),
    'privatevpn': ('#9f61b9', '#5b306c'),
    'pia': ('#6dc862', '#3a6b39'),
    'hotspot shield': ('#6DC0FA', '#3a72a3'),
    'strongvpn': ('#EEAA1D', '#9b630f')
}

# Function to assign colors based on provider names
def get_color(provider_name):
    provider_name = provider_name.lower()
    return vpn_colors.get(provider_name, ('#4b4b4b', '#2a2a2a'))

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
                'backgroundColor': [f'rgba(0,0,0,0)' for _ in colors],
                'borderWidth': 1
            }]
        else:
            for col in mapped_columns.values():
                values = source_data[col].tolist()
                colors = [get_color(provider) for provider in labels]
                datasets.append({
                    'label': f'{col} ({measurement_unit})',
                    'data': values,
                    'backgroundColor': [f'rgba(0,0,0,0)' for _ in colors],
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
            var gradientPlugin = {{
                id: 'customGradient',
                beforeDatasetsDraw: function(chart, options, pluginOptions) {{
                    var ctx = chart.ctx;
                    chart.data.datasets.forEach((dataset, i) => {{
                        var gradient = ctx.createLinearGradient(0, 0, 0, chart.height);
                        gradient.addColorStop(0, '{vpn_colors[labels[0].lower()][0]}');
                        gradient.addColorStop(1, '{vpn_colors[labels[0].lower()][1]}');
                        dataset.backgroundColor = gradient;
                    }});
                }}
            }};
            var vpnSpeedChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: {json.dumps(datasets)}
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        customGradient: {{}},
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
                }},
                plugins: [gradientPlugin]
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
