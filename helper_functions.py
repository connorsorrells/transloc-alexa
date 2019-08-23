"""
This module acts as helper code for the Transloc skill for
Amazon's Alexa platform. This code gets a current list of all stops
for the specified agency. It uses an API (with necesarry API key)
to obtain the stops information from TransLoc.

@author: Connor Sorrells

Example usage of the functions:
e = get_all_stops()
export_to_csv(e)
"""

import requests

# should not have to change API_BASE unless API version is updated
API_BASE = "https://transloc-api-1-2.p.mashape.com"
API_KEY = "ENTER_YOUR_API_KEY_HERE"
AGENCY_CODE = "ENTER_YOUR_AGENCY_CODE_HERE"

def get_all_stops():
    headers = { "X-Mashape-Key": API_KEY, "Accept": "application/json" }
            
    s = requests.Session()
    s.headers.update(headers)

    url_stops = API_BASE + "/stops.json?agencies=" \
    + AGENCY_CODE + "&callback=call"
	try:
		response_stops = s.get(url_stops)
		all_stops = response_stops.json()
	except requests.exceptions.RequestException as e:
        print("Error occured while calling API: ", e)
    
    stop_ids = []
    names = []
    for data in all_stops["data"]:
        stop_id = data["stop_id"]
        stop_ids.append(stop_id)
        name = data["name"]
        names.append(name)
        
    names_stops= []
    for i in range(len(stop_ids)):
        name_stop = []
        name = names[i]
        name_stop.append(name)
        stop_id = stop_ids[i]
        name_stop.append(stop_id)
        names_stops.append(name_stop)
    return names_stops


def export_to_csv(stops, filename="stops.csv"):
    try:
        output_file = open(filename, 'w')
        for row in stops:
            for column in row:
                output_file.write(column + ",")
            output_file.write("\n")
        output_file.close()
    except Exception as exc:
        print("Error occurred while saving stops:", exc)
