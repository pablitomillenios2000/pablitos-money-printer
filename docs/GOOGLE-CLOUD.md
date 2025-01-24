
# Google Cloud Server

create a google cloud vm

Use the latest ubuntu LTS operating system (needs to be changed manually)

once the VM is running, run install_dependencies.sh

allow http and https traffic on the machine creation page

edit the firewall rules to allow "all protocols and ports"

servers should bind to host='0.0.0.0'

app.run(host='0.0.0.0', port=9500)