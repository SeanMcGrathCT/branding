import streamlit as st
import pandas as pd
import json

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
    
    # Input SEO title and description
    seo_title = st.text_input("Enter the SEO title for the chart:")
    seo_description = st.text_area("Enter the SEO description for the chart:")
    
    if st.button("Generate HTML"):
        # Extract data for the chart
        labels = source_data[label_column].tolist()
        
        if chart_type == "Single Bar Chart":
            values = source_data[mapped_columns[label_column]].tolist()
            datasets = [{
                'label': 'Speed (Mbps)',
                'data': values,
                'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            }]
        else:
            datasets = []
            colors = ['rgba(75, 192, 192, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(153, 102, 255, 0.6)',
                      'rgba(255, 159, 64, 0.6)', 'rgba(255, 99, 132, 0.6)', 'rgba(255, 206, 86, 0.6)',
                      'rgba(75, 192, 192, 0.6)', 'rgba(54, 162, 235, 0.6)']
            border_colors = ['rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)', 'rgba(153, 102, 255, 1)',
                             'rgba(255, 159, 64, 1)', 'rgba(255, 99, 132, 1)', 'rgba(255, 206, 86, 1)',
                             'rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)']
            for idx, (col, color, border_color) in enumerate(zip(mapped_columns.values(), colors, border_colors)):
                values = source_data[col].tolist()
                datasets.append({
                    'label': col,
                    'data': values,
                    'backgroundColor': color,
                    'borderColor': border_color,
                    'borderWidth': 1
                })
        
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
</head>
<body>
    <div style="width: 100%; max-width: 800px; margin: 0 auto;">
        <canvas id="vpnSpeedChart"></canvas>
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
                            text: 'VPN Speed Comparison (Mbps)',
                            font: {{
                                size: 18
                            }}
                        }},
                        legend: {{
                            display: true
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Speed (Mbps)'
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
