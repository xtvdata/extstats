#!/opt/bin/python

#
# This is the main script to be called which will contain most of the logic in the former extstats.sh
# Must be imported extstats.py in order to use cached bytecode
# Since extstats.py will always be parsed, it is necessary to keep it as light as possible (i.e. just import "main" and start processing)
#
# test with cron line
# */5 * * * * /opt/bin/python /jffs/addons/extstats.d/main.py
# added to file: /var/spool/cron/crontabs/admin
#


def main(SCRIPT_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    if CONFIG['MODULES'].getboolean('BASIC'):
        from mod_basic import main as mod_basic
        mod_basic(SCRIPT_NAME, "mod_basic", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)
    if CONFIG['MODULES'].getboolean('VPN_CLIENTS'):
        from mod_vpn_client import main as mod_vpn_client
        mod_vpn_client(SCRIPT_NAME, "mod_vpn_client", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)
    if CONFIG['MODULES'].getboolean('VPN_SERVERS'):
        from mod_vpn_server import main as mod_vpn_server
        mod_vpn_server(SCRIPT_NAME, "mod_vpn_server", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)
    if CONFIG['MODULES'].getboolean('WIFI_CLIENTS'):
        from mod_wifi_clients import main as mod_wifi_clients
        mod_wifi_clients(SCRIPT_NAME, "mod_wifi_clients", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)
    if CONFIG['MODULES'].getboolean('CLIENTS_TRAFFIC'):
        from mod_client_traffic import main as mod_client_traffic
        mod_client_traffic(SCRIPT_NAME, "mod_client_traffic", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)
    if CONFIG['MODULES'].getboolean('SKYNET'):
        from mod_skynet import main as mod_skynet
        mod_skynet(SCRIPT_NAME, "mod_skynet", SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG)

if __name__ == "__main__":
    import sys, configparser
    import socket
    
    SCRIPT_NAME = "extstats"
    SCRIPT_DIR = "/jffs/addons/"+SCRIPT_NAME+".d"
    SCRIPT_CONF = "/jffs/addons/extstats.d/config.py.conf"
    SCRIPT_DEBUG = False if len(sys.argv)!=2 else bool(sys.argv[1])
    TEMP_FOLDER = "/opt/tmp"
    # loading config - including influxDB (but it should be read just once from the main script and passed on to modules to limit file access and parsing)
    CONFIG = configparser.ConfigParser()
    try:
        with open(SCRIPT_CONF, 'r') as configfile:
            CONFIG.read_file(configfile)
        # execute only if run as a script
        main(SCRIPT_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, socket.gethostname(), CONFIG)
    except Exception as e:
        print(e)
        traceback.print_exc()
