#!/opt/bin/python

#
# Requires:
# > opkg install python3-requests
#

import logging
import logging.handlers
import time
import traceback
from extstats_utilities import *


def mod_skynet(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    locationRaw = ""
    try:
        with open('/jffs/scripts/firewall-start', 'r') as firewallStartScript:
            while True:
                line = firewallStartScript.readline()
                lineContens = line.split()
                locationRaw = [s for s in lineContens if "skynetloc=" in s]
                if locationRaw: break
        if locationRaw:
            location = locationRaw[0][10:]
            countBlackList = 0
            countBlockList = 0
            try:
                with open(str(location)+"/skynet.ipset", 'r') as skynetIpsetFile:
                    for i, l in enumerate(skynetIpsetFile):
                        if "add Skynet-Black" in line: countBlackList += 1
                        if "add Skynet-Block" in line: countBlockList += 1
                        pass
                points = {
                    "IPs_blocked": countBlackList,
                    "IPs_ranged_blocked": countBlockList
                }
                if debug: printOutput(False, "router.skynet", str(points), "")
                exportToDb(dbClient, int(curDateNs), "router.skynet", {"host": routerHostname}, points, debug)
                return
            except Exception as e:
                print(e)
                traceback.print_exc()
                return
        else:
            return
    except Exception as e:
        print(e)
        traceback.print_exc()
        return


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    mod_skynet(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket

    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_skynet"
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
