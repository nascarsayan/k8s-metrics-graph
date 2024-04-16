import re
import os
import json
import subprocess
from typing import List

MOREFMAPPING_FILE = "./morefid2name.json"
GM_DEPLOPMENT_TPL_FILE = "./gm-deployment-tpl.json"
GM_DEPLOPMENT_FILE = "./gm-deployment.json"

def run_command(command: List[str]):
    print(f"Running command: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr != "":
            print(stderr)
        raise Exception(f"Failed to run command: {' '.join(command)}")
    return result.stdout.strip()


def get_morefid2name(vm_prefix: str):
    if os.path.exists(MOREFMAPPING_FILE):
        with open(MOREFMAPPING_FILE, "r") as f:
            return json.load(f)

    output = run_command(
        ['govc', 'find', '-i', '-l', '-k=true', '-type', 'm']
    )
    lines = output.strip().split("\n")
    morefid2name = {}
    for line in lines:
        # Match the pattern below, and get vm-150307  and '/Some datacenter/vm/some vm'
        # VirtualMachine:vm-150307  /Some datacenter/vm/some vm
        match = re.match(r"VirtualMachine:(vm-\d+)\s+(.+)", line)
        if match is None:
            print(f"Warning: Line did not match: '{line}'")
            continue
        morefid = match.group(1)
        vm_path = match.group(2)
        # get basename of vm_path
        vm_name = vm_path.split("/")[-1]
        if not vm_name.startswith(vm_prefix):
            continue
        morefid2name[morefid] = vm_name
    
    with open(MOREFMAPPING_FILE, "w") as f:
        json.dump(morefid2name, f, indent=2)
    return morefid2name

morefid2name = get_morefid2name("contoso-win22-")
exclude_monames = [
    "contoso-win22-050",
    "contoso-win22-051",
]

with open(GM_DEPLOPMENT_TPL_FILE, "r") as f:
    gm_deployment_tpl = json.load(f)

res_tpl = json.dumps(gm_deployment_tpl["resources"])

from copy import deepcopy
gm_deployment = deepcopy(gm_deployment_tpl)
gm_deployment["resources"] = []

for morefid, vm_name in morefid2name.items():
    if vm_name in exclude_monames:
        continue
    res = res_tpl.replace("{{moName}}", vm_name).replace("{{moRefId}}", morefid)
    gm_deployment["resources"].extend(json.loads(res))

gm_deployment["resources"] = sorted(gm_deployment["resources"], key=lambda x: x["name"])

with open(GM_DEPLOPMENT_FILE, "w") as f:
    json.dump(gm_deployment, f, indent=2)
