# Distributor ID: Ubuntu
# Description:    Ubuntu 24.04.1 LTS
# Release:        24.04
# Codename:       noble


sudo apt update
sudo apt install python3-pip -y
sudo apt install jq -y
sudo apt install brotli -y
pip install websocket-client --break-system-packages
pip install websockets --break-system-packages
#pip install python-websocket
pip install python-binance --break-system-packages
pip install binance --break-system-packages
pip install pandas tqdm  --break-system-packages
pip install bybit --break-system-packages
pip install json5 --break-system-packages
pip install brotli --break-system-packages
pip install --upgrade urllib3 six bravado bravado-core  --break-system-packages
