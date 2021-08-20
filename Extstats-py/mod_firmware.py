#!/opt/bin/python

#
# Requires:
#

#import logging
#import logging.handlers
import time
import traceback
from extstats_utilities import *


def mod_firmware(debug, routerHostname, dbClient):
    points = {}
    curDateNs = time.time() * 1000000000
    fwBuildNo = subprocess.run(["nvram", "get", "buildno"], stdout=subprocess.PIPE, text=True)
    if fwBuildNo.returncode==0 and len(fwBuildNo.stdout)>1:
        # points['build_no'] = str("v"+fwBuildNo.stdout[:-1])
        points['build_no'] = { "value": fwBuildNo.stdout[:-1, "type": "string"}]
        if debug: printOutput(False, "router.firmware", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.firmware", {"host": routerHostname}, points, debug)


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    mod_firmware(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket

    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_firmware"
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
