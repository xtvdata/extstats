#!/opt/bin/python
#
# Traffic logging tool for DD-WRT-based routers using InfluxDB
#
# Based on work from Emmanuel Brucy (e.brucy AT qut.edu.au)
# Based on work from Fredrik Erlandsson (erlis AT linux.nu)
# Based on traff_graph script by twist - http://wiki.openwrt.org/RrdTrafficWatch

# Edit by Corgan

# 1 https://www.instructables.com/id/How-to-graph-home-router-metrics/
#

#
# Note: This a draft to test data-gathering only - setup of the iptables rule is to be performed when the module is enable via the management shell script 
# Also the check of RRDIPT2 was omitted from this implementation since its scope is not clear in this context.
#
# All in all this module is just a "proof of concept"
#

from extstats_utilities import *
import subprocess
import time


def mod_client_traffic(debug, routerHostname, dbClient):
    metric="router.client_traffic"
    ##
    ## Note: this can probably be implemented much better using python-iptables (https://github.com/ldx/python-iptables)
    ##
    # get raw data - removed zeroing the table since influxdb can use differential operators
    curDateNs = time.time() * 1000000000
    rawData = subprocess.run(["iptables", "-L", "RRDIPT", "-vnx", "-t", "filter"], stdout=subprocess.PIPE, text=True)
    if rawData.returncode==0 and len(rawData.stdout)>1:
        # fetch additional data
        arpIpDict = loadArpIpDict()
        clientsDict = loadClientsDict()
        trafficElements = rawData.stdout.split("\n")
        trafficData = {}
        for i, trafficElement in enumerate(trafficElements[2:]):
            trafficDataRow = trafficElement.split()
            if len(trafficDataRow)==9 and trafficDataRow[8] != 'destination':
                if trafficDataRow[8] == '0.0.0.0/0':
                    # traffic is coming into router
                    if trafficData.get(trafficDataRow[7]) == None:
                        # need to create the client in the dictionary 1st
                        trafficData[trafficDataRow[7]] = {}
                    trafficData[trafficDataRow[7]]['pkts_recv'] = trafficDataRow[0]
                    trafficData[trafficDataRow[7]]['bytes_recv'] = trafficDataRow[1]
                else:
                    # traffic is going out to client
                    if trafficData.get(trafficDataRow[8]) == None:
                        # need to create the client in the dictionary 1st
                        trafficData[trafficDataRow[8]] = {}
                    trafficData[trafficDataRow[8]]['pkts_sent'] = trafficDataRow[0]
                    trafficData[trafficDataRow[8]]['bytes_sent'] = trafficDataRow[1]
        # send collected data to database
        for i, clientIp in enumerate(trafficData):
            tags = {"host": routerHostname, "ip": clientIp}
            # obtain client_mac
            client_macDict = arpIpDict.get(clientIp)
            if client_macDict:
                tags['client_mac'] = client_macDict['mac']
                client_nameDict = clientsDict.get(tags['client_mac'])
                if client_nameDict: tags['client_name'] = client_nameDict['name']
            exportToDb(dbClient, int(curDateNs), metric, tags, trafficData[clientIp], debug)


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    mod_client_traffic(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket
    
    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_client_traffic"
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
