#!/opt/bin/python

#
# Requires:


from extstats_utilities import *
import subprocess
import traceback
import time

wifiBands = {
    "eth6": 2.4,
    "eth7": 5
}

def parseInterface(itf, routerHostname, metric, dbClient, arpDict, clientsDict, dhcpDict, debug):
    # get mac addresses
    clientsRaw = subprocess.run(["wl", "-i", itf, "assoclist"], stdout=subprocess.PIPE, text=True)
    if clientsRaw.returncode==0 and len(clientsRaw.stdout)>1:
        clients = clientsRaw.stdout.split("\n")
        for i, client in enumerate(clients):
            if len(client)>10:
                mac = client[10:].lower()
                # check for IP address in arp table
                ip = ""
                if mac in arpDict:
                    ip = arpDict[mac]['ip']
                # check for station_name in dhcp clients table
                client_name = ""
                if mac in dhcpDict:
                    client_name = dhcpDict[mac]['name']
                elif mac in clientsDict:
                    client_name = clientsDict[mac]['name']
                points = { "wifiBand": wifiBands[itf] }
                wifiRaw = subprocess.run(["wl", "-i", itf, "sta_info", mac], stdout=subprocess.PIPE, text=True)
                curDateNs = time.time() * 1000000000
                if wifiRaw.returncode==0 and len(wifiRaw.stdout)>1:
                    wifiLines = wifiRaw.stdout.split("\n")
                    for i, l in enumerate(wifiLines):
                        if l.startswith("	 per antenna rssi of last rx data frame:"):
                            rssiLast = l[42:].split()
                            points['rssi_antenna1'] = int(rssiLast[0])
                            points['rssi_antenna2'] = int(rssiLast[1])
                            points['rssi_antenna3'] = int(rssiLast[2])
                            points['rssi_antenna4'] = int(rssiLast[3])
                        elif l.startswith("	 per antenna average rssi of rx data frames:"):
                            rssiAvg = l[46:].split()
                            points['rssi_antenna_avg_1'] = int(rssiAvg[0])
                            points['rssi_antenna_avg_2'] = int(rssiAvg[1])
                            points['rssi_antenna_avg_3'] = int(rssiAvg[2])
                            points['rssi_antenna_avg_4'] = int(rssiAvg[3])
                        elif l.startswith("	 per antenna noise floor:"):
                            noiseFloor = l[27:].split()
                            points['noise_antenna_1'] = int(noiseFloor[0])
                            points['noise_antenna_2'] = int(noiseFloor[1])
                            points['noise_antenna_3'] = int(noiseFloor[2])
                            points['noise_antenna_4'] = int(noiseFloor[3])
                        elif l.startswith("	 rate of last tx pkt:"):
                            txRate = l[23:].split()
                            points['tx1_rate_pkt'] = int(txRate[0])
                            points['tx2_rate_pkt'] = int(txRate[3])
                        elif l.startswith("	 rate of last rx pkt:"):
                            rxRate = l[23:].split()
                            points['rx_rate_pkt'] = int(rxRate[0])
                        elif l.startswith("link bandwidth ="):
                            linkBandwidth = l[17:].split()
                            points['link_bandwidth'] = int(linkBandwidth[0])
                        elif l.startswith("	 tx failures:"):
                            points['tx_failures'] = int(l[15:])
                        elif l.startswith("	 rx decrypt failures:"):
                            points['rx_decrypt_failures'] = int(l[23:])
                        elif l.startswith("	 idle"):
                            idleTime = l[7:].split()
                            points['idle'] = int(idleTime[0])
                        elif l.startswith("	 in network"):
                            onlineTime = l[13:].split()
                            points['online'] = int(onlineTime[0])
                        elif l.startswith("smoothed rssi: "):
                            points['rssi'] = int(l[15:])
                if debug: printOutput(False, name, str(points), "")
                tags = {"host": routerHostname, "interface": itf}
                if mac: tags['client_mac'] = mac
                if ip: tags['ip'] = ip
                if client_name: tags['client_name'] = client_name
                exportToDb(dbClient, int(curDateNs), metric, tags, points, debug)

def mod_wifi_clients(debug, routerHostname, dbClient):
    metric="router.wifi.clients"
    arpDict = loadArpDict()
    clientsDict = loadClientsDict()
    dhcpDict = loadDhcpDict()
    # load clients station names from 
    parseInterface('eth6', routerHostname, metric, dbClient, arpDict, clientsDict, dhcpDict, debug)
    parseInterface('eth7', routerHostname, metric, dbClient, arpDict, clientsDict, dhcpDict, debug)


def main(SCRIPT_NAME, MOD_NAME, SCRIPT_DIR, SCRIPT_DEBUG, TEMP_FOLDER, ROUTER_HOSTNAME, CONFIG):
    #dbClient = initInfluxDbClient(CONFIG['INFLUXDB'])
    dbClient = CONFIG
    mod_wifi_clients(SCRIPT_DEBUG, ROUTER_HOSTNAME, dbClient)

if __name__ == "__main__":
    import sys, configparser
    import socket
    
    SCRIPT_NAME = "extstats"
    MOD_NAME = "mod_wifi_clients"
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
