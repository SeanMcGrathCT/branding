def process_consolidated_data():
    global chart_js_files
    provider_names = []  # List to hold unique provider names
    overall_scores_data = {"streaming ability": [], "security & privacy": [], "overall score": []}
    processed_providers = set()  # To avoid duplicates
    speed_test_data_per_provider = {}

    for i, row in enumerate(consolidated_data):
        if row[0].lower() == 'url':  # Check if the row is a header row starting with 'URL'
            headers_row = row
            st.write(f"Found header row at index {i}: {headers_row}")

            # Process each provider row after the header row
            providers_data = consolidated_data[i + 1:]

            # Process each provider row
            for provider_row in providers_data:
                # Skip empty rows or rows without URLs or VPN Provider
                if not provider_row or not provider_row[0].startswith("http") or not provider_row[1]:
                    continue

                url = provider_row[0]
                provider_name = provider_row[1].strip()

                if provider_name not in processed_providers:  # Ensure unique providers
                    processed_providers.add(provider_name)
                    provider_names.append(provider_name)  # Add provider name once

                    # Fuzzy match columns related to speed tests
                    speed_test_columns = ["am", "noon", "pm"]
                    matched_speed_columns = [match_headers_with_scores(headers_row, col) for col in speed_test_columns]
                    matched_speed_columns = [col for col in matched_speed_columns if col]  # Filter out None

                    st.write(f"Matched Speed Test Columns: {matched_speed_columns}")

                    # Extract speed test data for the provider
                    provider_speed_data = []
                    for col in matched_speed_columns:
                        try:
                            score = provider_row[headers_row.index(col)]
                            provider_speed_data.append(float(score))  # Convert to float for chart data
                        except (ValueError, IndexError):
                            provider_speed_data.append(0)  # If there's an error, default to 0

                    speed_test_data_per_provider[provider_name] = provider_speed_data

                    # Process overall score columns
                    overall_score_columns = ["overall score", "streaming ability", "security & privacy"]
                    matched_overall_columns = [match_headers_with_scores(headers_row, col) for col in overall_score_columns]
                    matched_overall_columns = [col for col in matched_overall_columns if col]  # Filter out None

                    st.write(f"Matched Overall Score Columns: {matched_overall_columns}")

                    # Extract overall score data for the provider
                    for idx, col in enumerate(overall_score_columns):
                        if idx < len(matched_overall_columns) and matched_overall_columns[idx]:
                            try:
                                score = provider_row[headers_row.index(matched_overall_columns[idx])]
                                overall_scores_data[col].append(float(score))  # Convert to float
                            except (ValueError, IndexError):
                                overall_scores_data[col].append(0)  # Handle errors by adding a default value
                        else:
                            overall_scores_data[col].append(0)  # Ensure every provider has a score

    # Generate a single Chart.js for each overall score category for all providers
    for score_type, scores in overall_scores_data.items():
        overall_score_chart_js = f"""
        <div style="max-width: 805px; margin: 0 auto;">
            <canvas id="{score_type}_Chart" width="805" height="600"></canvas>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var ctx = document.getElementById('{score_type}_Chart').getContext('2d');
                var {score_type}_Chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(provider_names)},  # Unique provider names
                        datasets: [{{
                            label: 'VPN Providers {score_type.capitalize()}',
                            data: {json.dumps(scores)},  # Corresponding score data
                            backgroundColor: {json.dumps(['rgba(62, 95, 255, 0.8)'] * len(provider_names))},
                            borderColor: {json.dumps(['rgba(31, 47, 127, 0.8)'] * len(provider_names))},
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Score'
                                }}
                            }}
                        }},
                        plugins: {{
                            title: {{
                                display: true,
                                text: 'VPN Providers {score_type.capitalize()}'
                            }}
                        }}
                    }}
                }});
            }});
        </script>
        """
        chart_js_files.append((f"{score_type}_chart.txt", overall_score_chart_js))
