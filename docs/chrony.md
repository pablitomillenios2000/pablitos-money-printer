# Chrony: Linux real-time system clock sync

In order to run a 20-order-script you need to have your system time to be synchronized very frequently and very perfectly. This can be done using chrony


### Installation
sudo apt-get update
sudo apt-get install chrony

sudo systemctl enable chrony
sudo systemctl start chrony

Verify Tracking using:

chronyc tracking

### Config
edit:

sudo nano /etc/chrony/chrony.conf

and add

server pool.ntp.org iburst
server time.google.com iburst

then run:

sudo systemctl restart chrony

## Result

This should keep your linux time sharply up to date and prevent those errors