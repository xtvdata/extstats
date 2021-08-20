#!/opt/bin/python

#
# Requires:
#

from extstats_utilities import *
import time
import copy
import traceback

def mod_vpn_server(debug, routerHostname, dbClient):
    name="router.vpnServers"
    # TODO: need better check for active server (not good to do a file i/o per server just to test if it exists)
    for serverId in [1, 2]:
        try:
            curDateNs = time.time() * 1000000000
            with open("/etc/openvpn/server%d/status" % (serverId)) as f:
                tags = {
                    "host": routerHostname,
                    "vpn_server": str(serverId)
                }
                parsing_clientList = False
                parsing_routingTable = False
                parsing_globalStats = False
                for i, l in enumerate(f, 3):
                    if l.startswith("CLIENT_LIST,"):
                        # lets parse client elements
                        points = {}
                        clientElems = l.split(',')
                        clientTags = copy.deepcopy(tags)
                        clientTags['commonName'] = clientElems[1].replace(" ", "_")
                        clientTags['realAddress'] = clientElems[2]
                        clientTags['virtualAddress'] = clientElems[3]
                        # 6 is ipv6 address
                        points['bytesRecv'] = clientElems[5]
                        points['bytesSent'] = clientElems[6]
                        # 7 is connected since in string format
                        points['connectedSince'] = int(clientElems[8]) * 1000000000
                        clientTags['userName'] = clientElems[9].replace(" ", "_")
                        clientTags['clientId'] = clientElems[10]
                        clientTags['peerId'] = clientElems[11]
                        clientTags['dataChannelCipher'] = clientElems[12][:-1]
                        if debug: printOutput(False, name, str(points), str(clientTags))
                        exportToDb(dbClient, curDateNs, "router.vpnServers.clients", clientTags, points, debug)
                    elif l.startswith("ROUTING_TABLE,"):
                        pass
                        # # parse route
                        # # lets parse route elements
                        # points = {}
                        # routeElems = l.split(',')
                        # routeTags = copy.deepcopy(tags)
                        # routeTags['virtualAddress'] = routeElems[1]
                        # routeTags['commonName'] = routeElems[2].replace(" ", "_")
                        # routeTags['realAddress'] = routeElems[3]
                        # routeTags['lastRef'] = routeElems[5]
                        # routeTags['virtualAddress'] = routeElems[1]
                        # routeTags['virtualAddress'] = routeElems[1]
                        # routeTags['virtualAddress'] = routeElems[1]
                        # routeTags['virtualAddress'] = routeElems[1]
                        # if debug: printOutput(False, name, str(points), str(routeTags))
                        # exportToDb(dbClient, curDateNs, "router.vpnServers.routes", routeTags, points, debug)
                    elif l.startswith("TIME,"):
                        # we have the timestamp declared in the file, lets use it
                        timeParts=l.split(',')
                        curDateNs=float(timeParts[2]) * 1000000000
                    else:
                        pass
        except Exception as e:
            #print(e)
            pass


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    mod_vpn_server(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket
    
    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_vpn_server"
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
