clear
echo ""
echo "Stopping the server background processes"
echo ""
echo "Leaving the webserver running"
echo ""

pkill -f "python3 ./bucle"
pkill -f "python3 ./keep-fetching.py"

python3 /home/g1pablo_escaida1/pablitos-money-printer/src/python/binance/private/sell20_beta2.py

