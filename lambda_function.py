"""
This module acts as the backend code for a Transloc Rider skill for
Amazon's Alexa platform. It is intended to be implemented on Amazon's
cloud-based Lambda function or hosted by Alexa instead of a server. It uses an
API (with a necessary API key) to obtain the information from TransLoc.

@author: Connor Sorrells
"""

import requests
from datetime import datetime
from pytz import timezone

# should not have to change API_BASE unless API version is updated
API_BASE = "https://transloc-api-1-2.p.mashape.com"
API_KEY = "ENTER_YOUR_API_KEY_HERE"
AGENCY_CODE = "ENTER_YOUR_AGENCY_CODE_HERE"
AMAZON_SKILL_ID = "ENTER_YOUR_AMAZON_SKILL_ID_HERE"
TIMEZONE = "ENTER_YOUR_TIMEZONE_HERE"
TRANSIT_NAME = "ENTER_YOUR_TRANSIT_NAME_HERE"

def lambda_handler(event, context):
    if (event["session"]["application"]["applicationId"] != AMAZON_SKILL_ID):
        raise ValueError("Invalid Application ID")
    
    if event["request"]["type"] == "LaunchRequest":
        return on_launch(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])

def on_launch(launch_request, session):
    return get_welcome_response()

def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "GetBusTimes":
        return get_bus_times(intent)
    elif intent_name == "AMAZON.HelpIntent" or intent_name == "AMAZON.NavigateHomeIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")

def handle_session_end_request():
    card_title = TRANSIT_NAME + " - Thanks"
    speech_output = "Thank you for using the " + TRANSIT_NAME + " skill.  See you next time!"
    should_end_session = True
    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

def handle_exception():
    card_title = TRANSIT_NAME + " - Error"
    speech_output = "There was a problem getting the data. " \
                    "Please try again later. Goodbye."
    should_end_session = True
    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

def get_welcome_response():
    session_attributes = {}
    card_title = TRANSIT_NAME + " - Welcome"
    speech_output = "Welcome to the Alexa " + TRANSIT_NAME + " skill. " \
                    "You can ask me for bus times from any stop."
    reprompt_text = "Please ask me for bus times from a stop."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_bus_times(intent):
    session_attributes = {}
    card_title = TRANSIT_NAME + " - Arrivals"
    speech_output = "I'm not sure which stop you wanted bus times for. " \
                    "Please try again."
    reprompt_text = "I'm not sure which stop you wanted bus times for. " \
                    "Please try again."
    should_end_session = False

    if "resolutions" in intent["slots"]["Stop"] and intent["slots"]["Stop"] \
    ["resolutions"]["resolutionsPerAuthority"][0]["status"]["code"] == "ER_SUCCESS_MATCH":
        stop_name = intent["slots"]["Stop"]["resolutions"] \
                    ["resolutionsPerAuthority"][0]["values"][0]["value"]["name"]
        stop_code = intent["slots"]["Stop"]["resolutions"] \
                    ["resolutionsPerAuthority"][0]["values"][0]["value"]["id"]

        if (stop_code != "" and len(stop_code) == 7):
            card_title = TRANSIT_NAME + " - Arrivals at " + stop_name.title()

            headers = { "X-Mashape-Key": API_KEY, "Accept": "application/json" }
            
            s = requests.Session()
            s.headers.update(headers)

            url_arrivals = API_BASE + "/arrival-estimates.json?agencies=" \
            + AGENCY_CODE + "&callback=call&stops=" + stop_code
            try:
                response_arrivals = s.get(url_arrivals)
                stop_arrivals = response_arrivals.json()
            except requests.exceptions.RequestException as e:
                return handle_exception()
            
            if len(stop_arrivals["data"]) != 0:
                url_vehicles = API_BASE + "/vehicles.json?agencies=" \
                + AGENCY_CODE + "&callback=call"
                try:
                    response_vehicles = s.get(url_vehicles)
                    all_vehicles = response_vehicles.json()
                except requests.exceptions.RequestException as e:
                    return handle_exception()
            
                url_routes = API_BASE + "/routes.json?agencies=" \
                + AGENCY_CODE + "&callback=call"
                try:
                    response_routes = s.get(url_routes)
                    all_routes = response_routes.json()
                except requests.exceptions.RequestException as e:
                    return handle_exception()
                
                unique_vehicles = []
            
                now = datetime.now(timezone(TIMEZONE))

                speech_output = "Bus arrivals at " + stop_name + " are as follows: "
                for data in stop_arrivals["data"]:
                    for arrival in data["arrivals"]:
                        vehicle = arrival["vehicle_id"]
                        estimate = arrival["arrival_at"]
                        route = arrival["route_id"]
                        arrives = make_date_time_object(estimate)
                        if (vehicle not in unique_vehicles):
                            unique_vehicles.append(vehicle)
                            speech_output += "A bus on "
                            speech_output += get_route_output(all_routes, route)
                            speech_output += " route will arrive in "
                            speech_output += get_time_output(arrives, now)
                            speech_output += get_capacity_output(all_vehicles, vehicle)
                speech_output = speech_output[:-1] # get rid of last space
            else:
                speech_output = "There are currently no arrivals planned for " + stop_name + "."
            speech_output += " Would you like to ask for the bus times of another stop?"
            reprompt_text = "Which stop would you like the bus times for?"

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))
    
def make_date_time_object(iso_date_time):
    year = int(iso_date_time[0:4])
    month = int(iso_date_time[5:7])
    day = int(iso_date_time[8:10])
    hour = int(iso_date_time[11:13])
    minute = int(iso_date_time[14:16])
    second = int(iso_date_time[17:19])
    dt = datetime(year, month, day, hour, minute, second, 0)
    tz = timezone(TIMEZONE)
    dt = tz.localize(dt.replace(tzinfo=None))
    return dt
    
def get_time_output(arrival_time, now_time):
    minutes_diff = (int)((arrival_time - now_time).total_seconds() / 60.0)
    seconds_diff = (int)((arrival_time - now_time).total_seconds() % 60)
    speech_output = ""
    seconds_form = ""
    minutes_form = ""
    # get form of second/seconds
    if seconds_diff == 1:
        seconds_form = "second"
    else:
        seconds_form = "seconds"
    # get form of minute/minutes
    if minutes_diff == 1:
        minutes_form = "minute"
    else:
        minutes_form = "minutes"
    # just include seconds if less than a minute
    if minutes_diff < 1:
        speech_output += str(seconds_diff) + " " + seconds_form + " "
    # include minutes and seconds otherwise
    else:
        speech_output += str(minutes_diff) + " " + minutes_form + \
        " and " + str(seconds_diff) + " " + seconds_form + " "
    return speech_output

def get_capacity_output(vehicles_json, vehicle_id):
    speech_output = ""
    for vehicle in vehicles_json["data"][AGENCY_CODE]:
        if vehicle["vehicle_id"] == vehicle_id:
            if vehicle["passenger_load"] != None:
                capacity = vehicle["passenger_load"]
                capacity = capacity * 100.0
                capacity_string = "%.0f" %capacity 
                speech_output += "that is currently " + capacity_string + "% full. "
            else:
                speech_output += "that does not keep track of its capacity. "
    return speech_output
    
def get_route_output(routes_json, route_id):
    speech_output = ""
    for route in routes_json["data"][AGENCY_CODE]:
        if route["route_id"] == route_id:
            if route["long_name"] != None or route["long_name"] != "" :
                speech_output += "the " + route["long_name"]
            else:
                speech_output += "an unknown"
    return speech_output

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }
