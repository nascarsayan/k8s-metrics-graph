from datetime import timedelta
import os
import pandas as pd
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

curr_folder = os.path.dirname(os.path.abspath(__file__))
csv_folder = os.path.join(curr_folder, "psclient")
az_gm_data_csv = os.path.join(csv_folder, "az_gm_data.csv")
metrics_data_csv = os.path.join(csv_folder, "metrics_data.csv")

# Load the az_gm_data.csv
az_gm_data = pd.read_csv(az_gm_data_csv, parse_dates=["start_time", "end_time"])

# Load the metrics_data.csv
metrics_data = pd.read_csv(metrics_data_csv, parse_dates=["time"])

end_time_window = az_gm_data["end_time"].max() + timedelta(hours=1)

# filtered_metrics_data = metrics_data
# # Filter the metrics data based on the start and end times from az_gm_data
# filtered_metrics_data = metrics_data[
#     (metrics_data["time"] >= az_gm_data["start_time"].min())
#     & (metrics_data["time"] <= az_gm_data["end_time"].max())
# ]

filtered_metrics_data = metrics_data[(metrics_data["time"] <= end_time_window)]

# Remove 'Mi' from memory_bytes column
filtered_metrics_data["memory_bytes"] = (
    filtered_metrics_data["memory_bytes"].str.replace("Mi", "").astype(float)
)

# Remove 'm' from cpu_cores column
filtered_metrics_data["cpu_cores"] = (
    filtered_metrics_data["cpu_cores"].str.replace("m", "").astype(int)
)

# Create a separate plot for each container
containers = filtered_metrics_data["name"].unique()

out_dir = "psclient-data"

webpage_uris = []
webpage_base = f"https://nascarsayan.github.io/{out_dir}"

for container in containers:
    container_data = filtered_metrics_data[filtered_metrics_data["name"] == container]

    # Create an interactive line chart for CPU usage
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=container_data["time"],
            y=container_data["cpu_cores"],
            mode="lines",
            name="CPU Usage (Milli Cores)",
        )
    )
    fig.update_layout(
        title=f"{container} CPU Usage", xaxis_title="Time", yaxis_title="CPU Cores"
    )

    # Add markers for start and end times
    for index, row in az_gm_data.iterrows():
        fig.add_shape(
            dict(
                type="line",
                x0=row["start_time"],
                x1=row["start_time"],
                y0=0,
                y1=100,
                line=dict(color="red", dash="dash"),
                name="Deployment Start",
            )
        )
        fig.add_shape(
            dict(
                type="line",
                x0=row["end_time"],
                x1=row["end_time"],
                y0=0,
                y1=100,
                line=dict(color="green", dash="dash"),
                name="Deployment End",
            )
        )

    # fig.update_layout(legend_title_text="Legend", showlegend=True)

    file_name = f"{container}_cpu_usage.html"
    webpage_uri = f"{webpage_base}/{file_name}"
    webpage_uris.append(webpage_uri)
    fig.write_html(f"{out_dir}/{file_name}")

    # Create an interactive line chart for Memory usage
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=container_data["time"],
            y=container_data["memory_bytes"],
            mode="lines",
            name="Memory Usage (Bytes)",
        )
    )
    fig.update_layout(
        title=f"{container} Memory Usage",
        xaxis_title="Time",
        yaxis_title="Memory Bytes",
    )

    # Add markers for start and end times
    for index, row in az_gm_data.iterrows():
        fig.add_shape(
            dict(
                type="line",
                x0=row["start_time"],
                x1=row["start_time"],
                y0=0,
                y1=100,
                line=dict(color="red", dash="dash"),
                name="Deployment Start",
            )
        )
        fig.add_shape(
            dict(
                type="line",
                x0=row["end_time"],
                x1=row["end_time"],
                y0=0,
                y1=100,
                line=dict(color="green", dash="dash"),
                name="Deployment End",
            )
        )

    fig.update_layout(legend_title_text="Legend", showlegend=True)  

    file_name = f"{container}_memory_usage.html"
    webpage_uri = f"{webpage_base}/{file_name}"
    webpage_uris.append(webpage_uri)
    fig.write_html(f"{out_dir}/{file_name}")

with open(f"{out_dir}/webpage_uris.md", "w") as f:
    f.write("\n".join(webpage_uris))
