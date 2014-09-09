#!/usr/bin/env python
"""tintri_stats_summary - Uses Tintri REST API to get summary of performance stats.


pip install requests

"""
from __future__ import division    # So division of integers will result in float
import json
import time
import requests
from credentials import TINTRI_USER         # Login info now stored in credentials.py
from credentials import TINTRI_PASSWORD     # Login info now stored in credentials.py

__author__ = 'scott@flakshack.com (Scott Vintinner)'

#=================================SETTINGS======================================
TINTRI_LOGIN_URL = "https://tintri.yourcompany.domain/api/v300/flex/session/login/action=create"
TINTRI_STATS_SUMMARY = "https://tintri.yourcompany.domain/api/v300/flex/datastore/default/statsSummary/action=fetch"
TINTRI_VMSTATS = "https://tintri.yourcompany.domain/api/v300/flex/vm/action=fetch?limit=10&sortedBy=IOPS&queryType=TOP_DOCS_BY_LATEST_TIME&sortOrder=DESC"
SAMPLE_INTERVAL = 60
MAX_DATAPOINTS = 30
#===============================================================================


class TintriData:
    def __init__(self):
        self.iops = []
        self.latency = []
        self.throughput = []
        self.flash_hit = []
        self.space_used = []


class TintriNotConnectedException(Exception):
    pass


class MonitorJSON:
    """This is a simple class passed to Monitor threads so we can access the current JSON data in that thread"""
    def __init__(self):
        self.json = ""
        self.session = None
        self.data = TintriData()


def output_message(message):
    """This function will output an error message formatted in JSON to display on the StatusBoard app"""
    output = json.dumps({"error": message}, indent=4)
    return output



def generate_json(tintri_monitor):
    """This function will connect to the VNX web server, parse data and store the output in vnx_monitor.json"""
    try:


        login_payload = {
            "typeId": "com.tintri.api.rest.vcommon.dto.rbac.RestApiCredentials",
            "newPassword": None,
            "roles": None,
            "username": TINTRI_USER,
            "password": TINTRI_PASSWORD
        }
        headers = {'content-type': 'application/json'}


        # Here I'm processing the login each interval along with the request.  I tried using the existing
        # connection, but at some point the Tintri stops accepting the session.  It's messy, but until Tintri
        # releases some documentation, this is the best way to ensure that it keeps working.

        #if tintri_monitor.session is None:
        # Create Session object to persist JSESSIONID cookie (so the next requests to Tintri will work)
        tintri_monitor.session = requests.Session()

        # For all our requests, use the verify=False to ignore certificate errors
        r = tintri_monitor.session.post(TINTRI_LOGIN_URL, data=json.dumps(login_payload), verify=False, headers=headers)

        if r.status_code != 200:
            raise TintriNotConnectedException("Not connected to Tintri: " + r.text)

        # Grab stats data from Tintri
        r = tintri_monitor.session.get(TINTRI_STATS_SUMMARY, verify=False, headers=headers)
        summary_stats = (r.json())["tintriObjects"][0]


        # Save stat datapoints to our persistent monitor object
        tintri_monitor.data.iops.append(summary_stats["operationsTotalIops"])
        tintri_monitor.data.latency.append(summary_stats["latencyTotalMs"])
        tintri_monitor.data.throughput.append(summary_stats["throughputTotalMBps"])
        tintri_monitor.data.flash_hit.append(summary_stats["flashHitPercent"])
        tintri_monitor.data.space_used.append(summary_stats["spaceUsedGiB"])

        # If we already have the max number of datapoints in our list, delete the oldest item
        if len(tintri_monitor.data.iops) > MAX_DATAPOINTS:
            del(tintri_monitor.data.iops[0])
            del(tintri_monitor.data.latency[0])
            del(tintri_monitor.data.throughput[0])
            del(tintri_monitor.data.flash_hit[0])
            del(tintri_monitor.data.space_used[0])


        # Grab VM stats data from Tintri
        #r = tintri_monitor.session.get(TINTRI_VMSTATS, verify=False, headers=headers)
        #vm_stats = r.json()

        output = json.dumps({"stats": tintri_monitor.data.__dict__})

        # ====================================
        # Generate JSON output and assign to vnx_monitor object (for return back to caller module)
        tintri_monitor.json = output

    except Exception as error:
        tintri_monitor.json = output_message(error.message)

    if __debug__:
        print tintri_monitor.json



# If you run this module by itself, it will instantiate the MonitorJSON class and start an infinite loop printing data.
if __name__ == '__main__':
    monitor = MonitorJSON()
    while True:
        generate_json(monitor)
        # Wait X seconds for the next iteration
        time.sleep(SAMPLE_INTERVAL)