#!/opt/bin/python

#
# Requires:
#

from extstats_utilities import *
import time
import traceback

def mod_vpn_client(debug, routerHostname, dbClient):
    name="router.vpnClients"
    # TODO: need better check for active clients (not good to do a file i/o per client just to test if it exists)
    for clientId in [1, 2, 3, 4, 5]:
        try:
            curDateNs = time.time() * 1000000000
            with open("/etc/openvpn/client%d/status" % (clientId)) as f:
                tags = {
                    "host": routerHostname,
                    "vpn_client": str(clientId)
                }
                points = {}
                for i, l in enumerate(f, 3):
                    if l.startswith("TUN/TAP read bytes"):
                        points['tun_r'] = int(l[19:])
                    elif l.startswith("TUN/TAP write bytes"):
                        points['tun_w'] = int(l[20:])
                    elif l.startswith("TCP/UDP read bytes"):
                        points['tcp_r'] = int(l[19:])
                    elif l.startswith("TCP/UDP write bytes"):
                        points['tcp_w'] = int(l[20:])
                    elif l.startswith("Auth read bytes"):
                        points['auth_r'] = int(l[16:])
                if debug: printOutput(False, name, str(points), str(tags))
                exportToDb(dbClient, curDateNs, "router.vpnClients", tags, points, debug)
        except Exception as e:
            #print(e)
            pass


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    mod_vpn_client(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket
    
    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_vpn_client"
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
        main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, socket.gethostname(), CONFIG)
    except Exception as e:
        print(e)
        traceback.print_exc()
