clear
cd "./python/binance/data/"
python3 "tradeable.py"
sleep 1
clear
python3 "keep-fetching.py" --once
cd ../../../../
cd ./src/dist
pwd
python3 "recompute.py" 
cd ..
echo " "
echo "Data fetched and computed. Please refresh localhost:8000 now"
echo -e "\e]8;;http://localhost:8000\e\\Open localhost:8000 in the browser\e]8;;\e\\"
echo " "