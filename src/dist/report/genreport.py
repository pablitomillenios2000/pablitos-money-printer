#!/usr/bin/env python3

import time
import subprocess
import os

# Start the timer
start_time = time.time()

# Execute the commands
os.system("python3 ./countnegtrades.py")

# Execute the command
try:
    subprocess.run("sudo cp -r ../../view/* /usr/share/caddy", shell=True, check=True)
    print("Files copied successfully!")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
#os.system("beep")

# Stop the timer
end_time = time.time()