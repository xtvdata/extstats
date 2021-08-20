#!/opt/bin/python

#
# Requires:
# > opkg install python3-requests
#

import subprocess
import requests
import logging
import logging.handlers

# move to database module
# from influxdb import InfluxDBClient
# def initInfluxDbClient(influxDbConfig, servername, port, user, password, dbname, usessl, noverify):
#     servername = influxDbConfig['URL']
#     port = influxDbConfig['PORT']
#     user = influxDbConfig['USERNAME']
#     password = influxDbConfig['PASSWORD']
#     dbname = influxDbConfig['DATABASE']
#     usessl = influxDbConfig['USESSL']
#     noverify = influxDbConfig['NOVERIFY']
#     # TODO: should add a check for mandatory data in case of bad configuration
#     if(usessl == True):
#         if(noverify == True): return InfluxDBClient(servername, port, user, password, dbname, True, False)
#         else: return InfluxDBClient(servername, port, user, password, dbname, True, True)
#     else: return InfluxDBClient(servername, port, user, password, dbname)
# def exportToDb(dbClient, timestamp, metric, tags, data, debug):
#     point = { "measurement": metric, "time": timestamp, "fields": data, "tags": tags }
#     if debug: print('Inserting %d datapoints...'%(len(datapoints)))
#     response = dbClient.write_points([point])
#     if response == False:
#         print('Problem inserting points, exiting...')
#         exit(1)
#     if debug: t("Wrote %d, response: %s" % (len(datapoints), response))
def dump(obj):
   for attr in dir(obj):
       if hasattr( obj, attr ):
           print( "obj.%s = %s" % (attr, getattr(obj, attr)))

def exportToDb(dbClient, timestamp, metric, tags, points, debug):
    # escape spaces in tag values
    for key, value in tags.items(): tags[key] = value.replace(" ", "_")
    data = "{name},{tags} {points} {timestamp}".format(
        name=metric,
        tags=','.join([f'{key}={value}' for key, value in tags.items()]),
        points=','.join([f'{key}={value}' for key, value in points.items()]),
        timestamp=int(timestamp)
    )
    res = requests.post("http://"+dbClient.get('INFLUXDB', 'HOSTNAME')+":"+dbClient.get('INFLUXDB', 'PORT')+"/write", params = {
        "db": dbClient.get('INFLUXDB', 'DATABASE'),
        "u": dbClient.get('INFLUXDB', 'USERNAME'),
        "p": dbClient.get('INFLUXDB', 'PASSWORD')
    }, data=data)
    if res.status_code==400:
        print("Bad request")
        print(res.text)
    elif res.status_code==401:
        print("Not authorized")
    elif res.status_code==404:
        print("Database not found (?)")

def getRouterModel():
    odmpid = subprocess.run(["nvram", "get", "odmpid"], stdout=subprocess.PIPE, text=True)
    if odmpid.returncode==0 and len(odmpid.stdout)>1:
        return odmpid.stdout
    else:
        prodid = subprocess.run(["nvram", "get", "productid"], stdout=subprocess.PIPE, text=True)
        if prodid.returncode==0 and len(prodid.stdout)>1:
            return prodid.stdout
        else:
            # TODO: add log for error handling
            return ""

def printOutput(shouldGoToSyslog, scriptName, message, level):
    if shouldGoToSyslog:
        my_logger = logging.getLogger('ExtStats')
        my_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.SysLogHandler(address = '/dev/log')
        my_logger.addHandler(handler)
        # TODO: should manage better the log level - now everything is considered a warning
        my_logger.warning(message)
    else:
        print("%s: %s %s" % (scriptName, level, message))

def logErrorToSyslog(message, err):
    my_logger = logging.getLogger('ExtStats')
    my_logger.setLevel(logging.ERROR)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    my_logger.addHandler(handler)
    # TODO: should manage better the log level - now everything is considered a warning
    my_logger.error(message)
    if err:
        logging.exception('Got exception on main handler')
        raise

def file_len(fname):
    try:
        with open(fname) as f:
            i=0
            for i, l in enumerate(f, 1):
                pass
            return i
    except Exception as e:
        print(e)
        traceback.print_exc()
        return 0


def loadArpDict():
    # load arp data
    arpDict = {}
    with open('/proc/net/arp', 'r') as f:
        for i, l in enumerate(f):
            if i>0: # skip the first line
                elems = l.split()
                if len(elems) == 6:
                    arpDict[elems[3].lower()] = {
                        "ip": elems[0]
                    }
                    # can also add "flags": elems[2]
                    # and/or "dev": elems[5]
                    # but there is no point in extracting them if they are not used
    return arpDict
def loadArpIpDict():
    # load arp data
    arpIpDict = {}
    with open('/proc/net/arp', 'r') as f:
        for i, l in enumerate(f):
            if i>0: # skip the first line
                elems = l.split()
                if len(elems) == 6:
                    arpIpDict[elems[0]] = {
                        "mac": elems[3].lower()
                    }
    return arpIpDict
def loadClientsDict():
    # load client data list
    clientsDict = {}
    with open('/opt/tmp/client-list.txt', 'r') as f:
        for i, l in enumerate(f):
            if len(l)>19: # skip unsplittable content
                macUc = l[-18:-1]
                clientsDict[macUc.lower()] = {
                    "name": l[:-19]
                }
    return clientsDict
def loadDhcpDict():
    # load dhcp client data list
    dhcpDict = {}
    # I dont use the dhcp from the router, thus I don't know the format of the file...
    #with open('/opt/tmp/dhcp_clients_mac.txt', 'r') as f:
    #    for i, l in enumerate(f, 1):
    #        macUc = l[-18:]
    #        dhcpDict[macUc.lower()] = {
    #            "name": l[:-19]
    #        }
    return dhcpDict