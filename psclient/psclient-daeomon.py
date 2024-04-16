import os
import subprocess
import threading
import datetime
from time import sleep
from typing import List

# Define the Azure CLI command and kubectl command
az_command = "az deployment group create --resource-group snaskar-psclient-rg --name psclient-gm-depl --template-file ./gm-deployment.json"
# az_command = "az group show --name snaskar-psclient-rg"
kubectl_command = "kubectl top -n azure-vmwareoperator pod --containers"
metrics_data_csv_file = "./metrics_data.csv"
az_gm_data_csv_file = "./az_gm_data.csv"
metrics_frequency_seconds = 15
az_frequency_seconds = 60 * 10

lock = threading.Lock()
az_completed = False

def run_command(command: List[str]):
    # print(f"Running command: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr != "":
            print(stderr)
        raise Exception(f"Failed to run command: {' '.join(command)}")
    return result.stdout.strip()

def get_time():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def run_az_command():
    global az_completed
    with lock:
        az_completed = False
    az_start_time = get_time()
    _ = run_command(az_command.split(" "))
    az_end_time = get_time()
    print_header = True
    if os.path.exists(az_gm_data_csv_file):
        print_header = False
    with open(az_gm_data_csv_file, "a") as f:
        if print_header:
            f.write("start_time,end_time\n")
        f.write(f"{az_start_time},{az_end_time}\n")
    with lock:
        az_completed = True

def run_kubectl_command():    
    print_header = True
    if os.path.exists(metrics_data_csv_file):
        print_header = False
    while True:
        metrics_data = []
        with lock:
            if az_completed:
                break
        current_time = datetime.datetime.utcnow()
        formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        res = run_command(kubectl_command.split(" "))
        """
POD                                        NAME                 CPU(cores)   MEMORY(bytes)
vmware-operator-manager-86f4557c85-97hwj   powershell-session   1m           100Mi
vmware-operator-manager-86f4557c85-97hwj   vmware-operator      4m           879Mi
        """
        lines = res.split("\n")
        # use first line as header
        header = lines[0]
        header_parts = [x.lower().replace("(", "_").replace(")", "") for x in header.split()]
        for line in lines[1:]:
            parts = line.split()
            if len(parts) != len(header_parts):
                continue
            metrics = {}
            for i in range(len(parts)):
                metrics[header_parts[i]] = parts[i]
            metrics["time"] = formatted_time
            metrics_data.append(metrics)

        # Write metrics data to csv file
        with open(metrics_data_csv_file, "a") as f:
            if print_header:
                f.write("time,pod,name,cpu_cores,memory_bytes\n")
                print_header = False
            for metrics in metrics_data:
                f.write(f"{metrics['time']},{metrics['pod']},{metrics['name']},{metrics['cpu_cores']},{metrics['memory_bytes']}\n")
        sleep(metrics_frequency_seconds)

iterations = 0
while True:
    print(f"{iterations+1}: Started")
    # Create threads for running both commands
    az_thread = threading.Thread(target=run_az_command)
    kubectl_thread = threading.Thread(target=run_kubectl_command)

    # Start both threads
    az_thread.start()
    print("Started az thread")
    kubectl_thread.start()
    print("Started kubectl thread")

    # Wait for both threads to finish
    az_thread.join()
    print("az thread finished")
    kubectl_thread.join()
    print("kubectl thread finished")
    
    print(f"{iterations+1}: Finished")
    iterations += 1

    print(f"Sleeping for {az_frequency_seconds} seconds")
    sleep(az_frequency_seconds)
