#!/usr/bin/env python3

import time
import subprocess
import os

# Start the timer
start_time = time.time()

command = ["sudo", "cp", "-r", "../view/*", "/usr/share/caddy"]

# Remove all .txt files
# os.system("rm ../view/output/*.txt")
# dont do this because you need the last_timestamp.txt

# Execute the commands
os.system("sudo python3 ./equity.py")
os.system("sudo python3 ./pairname.py")
os.system("sudo python3 ./compute_asset.py")
os.system("sudo python3 ./compute_poly_reg.py")
os.system("sudo python3 ./compute_instaspeed.py")
os.system("sudo python3 ./compute_instaspeed_abs.py")
os.system("sudo python3 ./compute_polyupdown.py")
os.system("sudo python3 ./compute_linreg.py")
#os.system("python3 ./compute_ema.py")
#os.system("python3 ./compute_sma.py")
#os.system("python3 ./slopedirection.py")
#os.system("python3 ./compute_ema_micro.py")
os.system("sudo python3 ./compute_trades_complex.py")
# os.system("python3 ./compute_trades_ema_algo_minloss.py")
# os.system("python3 ./compute_margin_requirement.py")
#os.system("python3 ./tradedirectionfilter.py") #filters non-steep
#os.system("python3 ./compute_unt_portfolio.py")
#os.system("python3 ./compute_final_portfolio_using_bnb.py")
#os.system("python3 ./compute_final_portfolio.py")
os.system("sudo bash ./compress_all.sh")

# Execute the command to remove old files and copy new ones
try:
    subprocess.run("sudo rm -rf /usr/share/caddy/*", shell=True, check=True)
    subprocess.run("sudo cp -r ../view/* /usr/share/caddy", shell=True, check=True)
    print("Files copied successfully!")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
#os.system("beep")

# Stop the timer
end_time = time.time()

# Calculate elapsed time
elapsed_time = end_time - start_time
print(f"Time taken for execution: {elapsed_time:.2f} seconds")

# Print human readable timestamp
print("Execution finished at:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
