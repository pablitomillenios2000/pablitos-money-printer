clear

echo "Diagnosing the following processes to be up:"
echo ""
ps aux | grep "caddy" | grep -v grep
ps aux | grep "python3 ./keep-fetching.py" | grep -v grep
ps aux | grep "python3 ./bucle" | grep -v grep
echo ""
echo "http.server, keep-fetching, bucle are the 3 processes"
echo "that make up a successfully running server"
