sudo apt install gnupg curl apt-transport-https cdebian-keyring debian-archive-keyring -y

sudo curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

sudo wget -qO - https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy.list

sudo apt update
sudo apt install caddy -y

cd /etc/caddy
sudo rm Caddyfile
sudo sudo cp /home/g1pablo_escaida1/CRYPTO-Trader/src/caddy/Caddyfile .
cd /home/g1pablo_escaida1/CRYPTO-Trader/

sudo systemctl start caddy
sudo systemctl enable caddy

echo " "
echo "please edit: /etc/caddy/Caddyfile with sudo nano"
echo "you have a sample file"