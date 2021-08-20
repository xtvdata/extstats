#!/opt/bin/python

#
# Requires:
# > opkg install python3-psutil
# > opkg install python3-requests
#

import logging
import logging.handlers
import time
import psutil
import subprocess
import traceback
import warnings
from extstats_utilities import *

def submod_cpu(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    # Note: psutils can get much more... - see https://psutil.readthedocs.io/en/latest/
    # used also in submod_mem
    cpuTimes = psutil.cpu_times()
    points = cpuTimes._asdict()
    sysLoad = psutil.getloadavg()
    points["load1"]=sysLoad[0]
    points["load5"]=sysLoad[1]
    points["load15"]=sysLoad[2]
    procs = psutil.pids()
    points["processes"]=len(procs)
    if debug: printOutput(False, "router.cpu", str(points), "")
    exportToDb(dbClient, int(curDateNs), "router.cpu", {"host": routerHostname}, points, debug)

def submod_mem(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    memoryRaw = psutil.virtual_memory()
    points = memoryRaw._asdict()
    if debug: printOutput(False, "router.mem", str(points), "")
    exportToDb(dbClient, int(curDateNs), "router.mem", { "host": routerHostname }, points, debug)

def submod_temp(debug, routerHostname, dbClient):
    points = {}
    curDateNs = time.time() * 1000000000
    temp_24 = subprocess.run(["wl", "-i", "eth6", "phy_tempsense"], stdout=subprocess.PIPE, text=True)
    if temp_24.returncode==0 and len(temp_24.stdout)>1:
        points['temp_24'] = float(temp_24.stdout.split(" ")[0]) * .5 + 20.0
    temp_50 = subprocess.run(["wl", "-i", "eth7", "phy_tempsense"], stdout=subprocess.PIPE, text=True)
    if temp_50.returncode==0 and len(temp_50.stdout)>1:
        points['temp_50'] = float(temp_50.stdout.split(" ")[0]) * .5 + 20.0
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as temp_cpu:
            temp_cpu_data = temp_cpu.read()
            points['temp_cpu'] = float(temp_cpu_data) / 1000
        if debug: printOutput(False, "router.temp", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.temp", {"host": routerHostname}, points, debug)
    except Exception as e:
        print(e)
        traceback.print_exc()

def submod_net(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    netData = psutil.net_io_counters(True, True)
    for key in netData:
        points = netData[key]._asdict()
        # can be improved with a reverse-lookup of the ip address
        if debug: printOutput(False, "router.network "+key, str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.network", {"host": routerHostname, "interface":key}, points, debug)

def submod_connections(debug, routerHostname, dbClient):
    points = {}
    curDateNs = time.time() * 1000000000
    points['dhcp_leases'] = file_len("/var/lib/misc/dnsmasq.leases")
    # read arp table and remove "incomplete"
    connected_clients = 0
    try:
        with open('/proc/net/arp', 'r') as arpTable:
            lineCount = 0
            while True:
                line = arpTable.readline()
                if not line: break
                else:
                    if lineCount>0:
                        lineDetails = line.split()
                        if lineDetails[2] != "0x0": connected_clients += 1
                    else: lineCount += 1
        points['connected_clients'] = connected_clients
        wifi_24 = subprocess.run(["wl", "-i", "eth6", "assoclist"], stdout=subprocess.PIPE, text=True)
        if wifi_24.returncode==0 and len(wifi_24.stdout)>1:
            points['wifi_24'] = len(wifi_24.stdout.split("\n")) - 1
        wifi_5 = subprocess.run(["wl", "-i", "eth7", "assoclist"], stdout=subprocess.PIPE, text=True)
        if wifi_5.returncode==0 and len(wifi_5.stdout)>1:
            points['wifi_5'] = len(wifi_5.stdout.split("\n")) - 1
        if debug: printOutput(False, "router.connections", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.connections", {"host": routerHostname}, points, debug)
    except Exception as e:
        print(e)
        traceback.print_exc()

def submod_uptime(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    try:
        with open('/proc/uptime', 'r') as uptime:
            uptimeRaw = uptime.readline()
            uptimeEls = uptimeRaw.split()
            # the second field is not used
            #points = { "uptime": uptimeEls[0], "uptime_idle": uptimeEls[1]}
            points = { "uptime": uptimeEls[0]}
            if debug: printOutput(False, "router.uptime", str(points), "")
            exportToDb(dbClient, int(curDateNs), "router.uptime", {"host": routerHostname}, points, debug)
    except Exception as e:
        print(e)
        traceback.print_exc()

def submod_filesystem(debug, routerHostname, dbClient):
    diskPartitions = psutil.disk_partitions()
    for partition in diskPartitions:
        mountpoint = partition.mountpoint
        device = partition.device
        fstype = partition.fstype
        curDateNs = time.time() * 1000000000
        partitionUsage = psutil.disk_usage(mountpoint)
        # could pull also I/O details per device with psutil.disk_io_counters()
        tags = {
            "host":   routerHostname,
            "device":     device,
            "mountedOn":  mountpoint,
            "filesystem": fstype
        }
        points = {
            "total":        partitionUsage.total,
            "used":         partitionUsage.used,
            "available":    partitionUsage.free,
            "usedPercent":  partitionUsage.percent
        }
        if debug: printOutput(False, "router.filesystem", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.filesystem", tags, points, debug)

def submod_swap(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    # This is to catch a recurrent warning due to stats not available on the router
    # /opt/lib/python3.9/site-packages/psutil/_pslinux.py:584: RuntimeWarning: 'sin' and 'sout' swap memory stats couldn't be determined and were set to 0
    # TODO: Possibly this check should be improved to filter only that warning from psutil.swap_memory()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        swapData = psutil.swap_memory()
        points = swapData._asdict()
        if debug: printOutput(False, "router.swap", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.swap", {"host": routerHostname}, points, debug)

def submod_firmware(debug, routerHostname, dbClient):
    curDateNs = time.time() * 1000000000
    fwBuildNo = subprocess.run(["nvram", "get", "buildno"], stdout=subprocess.PIPE, text=True)
    if fwBuildNo.returncode==0 and len(fwBuildNo.stdout)>1:
        points = {
            "build_no": fwBuildNo.stdout[:-1]
        }
        if debug: printOutput(False, "router.firmware", str(points), "")
        exportToDb(dbClient, int(curDateNs), "router.firmware", {"host": routerHostname}, points, debug)

def submod_divstats(debug, routerHostname, dbClient):
    # I dont use it, thus I dont know what it shuld do
    divstats="/jffs/addons/uiDivStats.d/uidivstats.txt"
    # original script
    # if [ -r "$divstats" ]; then
    #     CURDATE=`date +%s`
    #     TOTAL_D_BL=$(cat $divstats | grep "domains in total are blocked" | awk '{print $1}' | sed "s/,//g" )
    #     BLOCKED_BL=$(cat $divstats | grep "blocked by blocking list" | awk '{print $1}' | sed "s/,//g")
    #     BLOCKED_BLACKLIST=$(cat $divstats | grep "blocked by blacklist" | awk '{print $1}' | sed "s/,//g" )
    #     BLOCKED_WILDCARD=$(cat $divstats | grep "blocked by wildcard blacklist" | awk '{print $1}' | sed "s/,//g" )
    #     ADS_TOTAL_BL=$(cat $divstats | grep "ads in total blocked" | awk '{print $1}' | sed "s/,//g" )
    #     ADS_THIS_WEEK=$(cat $divstats | grep "ads this week, since last Monday" | awk '{print $1}' | sed "s/,//g" )
    #     NEW_ADDS=$(cat $divstats | grep "new ads, since" | awk '{print $1}' | sed "s/,//g" )
    #     name="router.uidivstats"
    #     columns="host=${ROUTER_MODEL}"
    #     divstats_data="$name,$columns domain_total_blocked=$TOTAL_D_BL,blocked_by_blocking_list=$BLOCKED_BL,blocked_by_blacklist=$BLOCKED_BLACKLIST,blocked_by_wildcard_blacklist=$BLOCKED_WILDCARD,ads_total_blocked=$ADS_TOTAL_BL,ads_this_week=$ADS_THIS_WEEK,new_ads=$NEW_ADDS ${CURDATE}000000000"
    #     Print_Output "${SCRIPT_debug}" "$divstats_data" "$WARN"
    #     $dir/export.sh "$divstats_data" "$SCRIPT_debug"
    # else
    #     Print_Output "${SCRIPT_debug}" "$uidivstats not found" "$WARN"
    # fi
    return


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    #import http.client as http_client
    #http_client.HTTPConnection.debuglevel = 1
    # You must initialize logging, otherwise you'll not see debug output.
    #logging.basicConfig()
    #logging.getLogger().setLevel(logging.DEBUG)
    #requests_log = logging.getLogger("requests.packages.urllib3")
    #requests_log.setLevel(logging.DEBUG)
    #requests_log.propagate = True

    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG # if switching to influxdb python client this should be the entry point to a shared session to send data
    submod_cpu(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_mem(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_temp(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_net(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_connections(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_uptime(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_firmware(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_filesystem(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    submod_swap(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)
    ##submod_divstats(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket

    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_basic"
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
