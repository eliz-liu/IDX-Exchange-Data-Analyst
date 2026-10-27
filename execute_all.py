import os
import sys


python_files = [script for script in os.listdir() if script.endswith('final_deliverable.py')]

os.remove("transform_log.csv")

for script in python_files:
    print(f"Running {script}...")
    rc = os.system(f'{sys.executable} "{script}"')

    if rc != 0:
        print(f"Failed: {script} (exit code {rc})")
        break
    else:
        print(f"Completed: {script}")
