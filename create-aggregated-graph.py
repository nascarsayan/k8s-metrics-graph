import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta

# Load the az_gm_data.csv
az_gm_data = pd.read_csv("az_gm_data.csv", parse_dates=["start_time", "end_time"])

# Define a time window that extends 1 hour beyond the end time
end_time_window = az_gm_data["end_time"].max() + timedelta(hours=1)

# Load the metrics_data.csv
metrics_data = pd.read_csv("metrics_data.csv", parse_dates=["time"])

# Filter the metrics data based on the start time and the extended end time window
filtered_metrics_data = metrics_data[
    (metrics_data["time"] >= az_gm_data["start_time"].min())
    & (metrics_data["time"] <= end_time_window)
]

# Remove 'Mi' from memory_bytes column
filtered_metrics_data["memory_bytes"] = (
    filtered_metrics_data["memory_bytes"].str.replace("Mi", "").astype(float)
)

# Remove 'm' from cpu_cores column
filtered_metrics_data["cpu_cores"] = (
    filtered_metrics_data["cpu_cores"].str.replace("m", "").astype(int)
)

# Create interactive line charts for each container's CPU and Memory usage
containers = filtered_metrics_data["name"].unique()

container_alias = {
    "vmware-operator": "operator",
    "powershell-session": "ps",
}

subplot_titles = [
    f"{container_alias.get(container, container)} {metric}"
    for metric in ["CPU", "Mem"]
    for container in containers
]

# Create a subplot with 2 rows and 2 columns
fig = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=subplot_titles,
)

metricMap = {
    "cpu": {
        "title": "CPU m",
        "csv_header": "cpu_cores",
    },
    "memory": {
        "title": "Mem Mi",
        "csv_header": "memory_bytes",
    },
}

markerMap = {
    "start": {
        "color": "red",
        "csv_header": "start_time",
        "title": "Start Time",
    },
    "end": {
        "color": "green",
        "csv_header": "end_time",
        "title": "End Time",
    },
}

for i, container in enumerate(containers):
    container_data = filtered_metrics_data[filtered_metrics_data["name"] == container]
    for j, metric in enumerate(["cpu", "memory"]):
        row, col = j + 1, i + 1
        title = metricMap[metric]["title"]
        csv_header = metricMap[metric]["csv_header"]
        # Create the CPU Usage chart
        fig.add_trace(
            go.Scatter(
                x=container_data["time"],
                y=container_data[csv_header],
                mode="lines",
                name=title,
            ),
            row=row,
            col=col,
        )
        fig.update_xaxes(title_text="Time", row=row, col=col)
        fig.update_yaxes(title_text=title, row=row, col=col)

        # Add markers for start and end times
        for index, az_start_end in az_gm_data.iterrows():
            for marker in ["start", "end"]:
                color = markerMap[marker]["color"]
                csv_header = markerMap[marker]["csv_header"]
                title = markerMap[marker]["title"]
                fig.add_shape(
                    dict(
                        type="line",
                        x0=az_start_end[csv_header],
                        x1=az_start_end[csv_header],
                        y0=0,
                        y1=10,
                        line=dict(color=color, dash="dash"),
                        name=title,
                    ),
                    row=row,
                    col=col,
                )

out_dir = "psclient-data"

# Update the layout and show the combined plot
fig.update_layout(title_text="CPU and Memory Usage for Containers")
# fig.update_layout(legend_title_text="Legend", showlegend=True)
fig.write_html(f"{out_dir}/metrics.html")
