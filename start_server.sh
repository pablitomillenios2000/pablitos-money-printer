#!/bin/bash

clear
echo ""

sudo rm /usr/share/caddy/output/equity.*
sudo rm /home/g1pablo_escaida1/CRYPTO-Trader/src/view/output/equity.*

# File containing the JSON data
CONFIG_FILE="./src/dist/apikey-crypto.json"

# Convert JSON5 to JSON by stripping comments and extra commas
JSON=$(sed '/^[[:space:]]*\/\//d; s/[[:space:]]*\/\/.*$//; /^[[:space:]]*$/d' "$CONFIG_FILE" | sed ':a;N;$!ba;s/,\n[[:space:]]*}/}/g')

# Read the JSON keys using jq
PAIR=$(echo "$JSON" | jq -r '.pair')
EXCHANGE=$(echo "$JSON" | jq -r '.exchange')
INPUT_FILE=$(echo "$JSON" | jq -r '.input_file')

# Print the results
echo "Pair: $PAIR"
echo "Exchange: $EXCHANGE"
echo "Input File: $INPUT_FILE"
echo ""
echo "Please double-check the .json file to be sure"
echo ""


echo ""
echo "starting the permanent data fetcher"
rm ./src/start_protocol/keep_fetching.log
cd "src/python/binance/data/"
#cd "src/python/${EXCHANGE}/data/"

./keep-fetching.py > ../../../start_protocol/keep_fetching.log & disown $!
cd ../../../../

echo "Waiting for 100 seconds with a progress bar..."
# Progress bar for 100 seconds
total=30
for ((i = 0; i <= total; i++)); do
    # Calculate progress percentage
    progress=$((i * 100 / total))
    # Display the progress bar
    printf " "
    printf " "
    printf "\rProgress: [%-50s] %d%%" "$(printf '#%.0s' $(seq 1 $((i * 50 / total))))" "$progress"
    sleep 1
done
echo ""
echo ""

echo "starting the recompute bucle"
rm ./src/start_protocol/bucle.log
cd ./src/dist
nohup ./bucle.py > ../start_protocol/bucle.log 2>&1 &

echo ""

sudo python3 ./recompute.py

echo ""

echo "Server start has been triggered. Please load localhost now"
