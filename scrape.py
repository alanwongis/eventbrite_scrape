#!/bin/python3
""" scrapes the Eventbrite.com website for car related events

    Version date: July 10, 2022
    Licence: MIT
    Copyright: Alan Wong

"""

import json
import logging
import pprint
import re
import time

import requests
from bs4 import BeautifulSoup

START_PAGE_NUM = 1
MAX_SEARCH_PAGES = 60  # set this to the max pages to scan on Eventbrite
SEARCH_URLS = [
    "https://www.eventbrite.com/d/united-states/auto-boat-and-air--events/?page=",
    "https://www.eventbrite.com/d/canada/auto-boat-and-air--events/automotive/?page=",
    "https://www.eventbrite.com/d/united-kingdom/auto-boat-and-air--events/automotive/?page=",
    "https://www.eventbrite.com/d/australia/auto-boat-and-air--events/automotive/?page="]

# filtering events uses keywords to decide to which events are car related events
# However some only contain keywords which are ambiguous (e.g. "Cruise in Chigago") which
# could be car related "Cruise down the Boulevard" vs "Cruise down the Mississippi"
# Until we implement better filter or have a way top curate the results, we'll
# exclude these items
INCLUDE_GREY_LIST = False

# threshold white term number in a description that switches an event to the white list
# (set to something useful)
WHITE_SCORE_THRESHOLD = 3

# if any of the following terms show up, definitely keep
WHITE_TERMS = [
    " car ", " car,", " car/", "porsche", "volkswagen", "vehicle", "motorcar", "motorshow",
    " cars ", "cars,", "car-", "tesla", "motorsport", "jeep", "chrysler", "ferrari", "volvo",
    "toyota", " audi ", " alfa ", " lotus", "automotive", "automobile", " vw ", "lexus",
    "nissan", "mercedes", "subaru", " auto ", "truck", "vette", "electric vehicle", "bmw",
    "track day", "speedway", "garage", "summit racing", "demolition", "demo derby", "cadillac",
    "low rider", " tires", "hot rod", "hotrod", "rods", "rally", "mustang", "driving",
    "wheels", "range rover", "fuel", "supercar", "driver"]

# .. but any of these, reject
BLACK_TERMS = [
    "boat", "yacht", "ships", " ship", "booze", "aviation", "aircraft",
    "airshow", "sail", "fishing", "fisherman", "air show", "aerospace",
    "party cruise", "dance cruise", "regatta", "dinner cruise", "brunch cruise",
    "breakfast cruise", "sunset cruise", "harbor cruise", "fireworks cruise",
    "siteseeing cruise", "drinks", "beer", "drone", "escooter",
    "helicopter", " sail ", "boobs", "party bus", "dancing", "kayak",
    "paddle", "music festival", "ballooning", "balloon", "drinks",
    "waterway", "pilot", "airplane", "whale watching", "party", "dj", "river cruise",
    "weekend cruise", "beer cruise", "wine", "ferry", " dock"]

# these terms actually aren't used, but are put here for reference.
# For example, you would expect "ride" to be a white term, but it triggers
# incorrectly on "boat ride".
GREY_TERMS = ["cruise", "ride", "ford", "concours", "drive", "parking"]

save_raw_dump = False  # flag to save the raw scrape

auth_token = open("eventbrite_api_key.txt",
                  "r").read()  # need a developer API key from Eventbrite. See "https://www.eventbrite.com/platform/api#/introduction/authentication"

my_headers = {'Authorization': f'Bearer {auth_token}'}

logging.basicConfig(filename='scrape.log', level=logging.WARNING)


def _get(endpoint):
    try:
        response = requests.get(endpoint, headers=my_headers, timeout=10)
        response.raise_for_status()
        # process response
        data = response.json()
        pprint.pprint(data)
        return data
    except requests.exceptions.HTTPError as errh:
        print(errh)


def get_page(url, n):
    # get the html for the page n of the search
    response = requests.get(url + str(n))
    raw_html = response.text
    soup = BeautifulSoup(raw_html, features='html.parser')
    return soup


def get_ticketing(event_id):
    # use the Eventbrite /Events/ endpoint to get the ticket info on a particular event
    response = requests.get(f"https://www.eventbriteapi.com/v3/events/{event_id}/?expand=ticket_availability",
                            headers=my_headers, timeout=10)
    return json.loads(response.text)


def get_description_body(event_id):
    """get the html portion of an Eventbrite event description"""
    response = requests.get(f"https://www.eventbriteapi.com/v3/events/{event_id}/structured_content/?purpose=listing",
                            headers=my_headers, timeout=10)
    data = json.loads(response.text)
    text = ""
    for module in data["modules"]:
        if "body" in module["data"]:
            text = text + module["data"]["body"]["text"]
    return text


def convert(raw_entry):
    """returns a dict conforming to the contracted json format

    Converts the raw eventbrite event into the contracted json format
    """
    converted = {}

    converted["name"] = raw_entry["name"]
    converted["description"] = raw_entry["summary"]
    if converted["description"] == None:  # sometimes summary is missing
        converted["description"] = ""
    converted["bookingUrl"] = raw_entry["url"]
    converted["eventType"] = "public"

    logging.debug(converted['name'].encode("ascii", "ignore"))

    converted["address"] = {
        "addressLineOne": "",
        "addressLineTwo": "",
        "city": "",
        "state": "",
        "country": "",
        "geolocation": {
            "latitude": "",
            "longitude": ""}}
    # sometimes the address is incomplete, i.e. missing
    # the addresss_1 fields, etc. so fill in as best
    # as possible. Usually latitude and longitude
    # exist so start with those.
    try:
        r_addr = raw_entry["primary_venue"]["address"]
        converted["address"]["geolocation"]["latitude"] = r_addr["latitude"]
        converted["address"]["geolocation"]["longitude"] = r_addr["longitude"]
        converted["address"]["country"] = r_addr["country"]
        converted["address"]["state"] = r_addr["region"]
        converted["address"]["city"] = r_addr["city"]
        converted["address"]["addressLineOne"] = r_addr["address_1"]
        converted["address"]["addressLineTwo"] = r_addr["address_2"]
    except:
        logging.info("missing address info for: %s" % converted["name"].encode("ascii", "ignore"))
        logging.info(str(r_addr))

    try:
        r_img = raw_entry["image"]["original"]
        converted["coverImage"] = {
            "url": r_img["url"],
            "width": str(r_img["width"]),
            "height": str(r_img["height"]),
            "thumbnail": "",
            "caption": "",
            "mediaType": "P"}
    except KeyError:
        logging.info("no image for- %s" % converted["name"].encode("ascii", "ignore"))
        converted["coverImage"] = {}  # no image

    try:
        eventbrite_event_id = raw_entry["id"]
        # do a request for ticket info
        raw_ticketing = get_ticketing(eventbrite_event_id)
        if raw_ticketing["is_free"] == True:
            converted["price"] = {"currency": "USD", "value": "0.00"}
        else:
            converted["price"] = {
                "currency": raw_ticketing["ticket_availability"]["maximum_ticket_price"]["currency"],
                "value": raw_ticketing["ticket_availability"]["maximum_ticket_price"]["major_value"]}
    except:
        logging.error("error setting ticket price on %s" % converted['name'].encode("ascii", "ignore"))
        # no price means free or by donation
        converted["price"] = {"currency": "USD", "value": "0.00"}

    converted["startDate"] = raw_ticketing["start"]["local"]
    converted["endDate"] = raw_ticketing["end"]["local"]
    converted["startDateUTC"] = raw_ticketing["start"]["utc"]
    converted["endDateUTC"] = raw_ticketing["end"]["utc"]
    converted["timezone"] = raw_ticketing["start"]["timezone"]

    converted["maximumNumberOfAvailableSpots"] = None
    converted["webex"] = ""
    converted["socialMedias"] = []

    return converted


def white_score(st):
    """counts the number of white term occurences"""
    c = 0
    for t in WHITE_TERMS:
        c += st.count(t)
    return c


def black_score(st):
    """counts the number of white term occurences"""
    c = 0
    for t in BLACK_TERMS:
        c += st.count(t)
    return c


def has_white_term(st):
    """returns True if the string contains a WHITE_TERMS"""
    st = st.lower()
    is_white = False
    for t in WHITE_TERMS:
        if st.find(t) >= 0:
            is_white = True
            break
    return is_white


def has_black_term(st):
    """returns True if the string contains a BLACK_TERMS"""
    st = st.lower()
    is_black = False
    for t in BLACK_TERMS:
        if st.find(t) >= 0:
            is_black = True
            break
    return is_black


def filter_non_car(events):
    white_events = []
    grey_events = []

    for ev in events:
        ev_name = ev["name"].lower()
        try:
            ev_summary = ev["summary"].lower()
        except:
            ev_summary = ""
        # look for terms in the white list(always add)
        if has_white_term(ev_name + ev_summary):
            white_events.append(ev)
        elif has_black_term(ev_name + ev_summary):  # look for terms in the black list
            logging.info("Non-car event: %s" % ev["name"].encode("ascii", "ignore"))
        else:
            # anything else we can't decisively categorize, is on the grey list, log for future review
            logging.info("car event? : %s" % ev["name"].encode("ascii", "ignore"))
            if INCLUDE_GREY_LIST:
                white_events.append(ev)
            else:
                grey_events.append(ev)

    return white_events, grey_events


def extract_entries(html):
    # on search results page, find the embedded <script> block which holds the auto related events
    events = html("script")
    for ev in events:
        raw_string = str(ev.string)
        if raw_string.find("window.__i18n__") >= 0:
            block_start_txt = " window.__SERVER_DATA__ = "
            start = raw_string.find(block_start_txt) + len(block_start_txt)
            block_end_txt = "window.__REACT_QUERY_STATE__ "
            end = raw_string.find(block_end_txt) - 1
            data = json.loads(raw_string[start:end].strip()[:-1])
    entries = data["search_data"]["events"]["results"]
    logging.info("%i found on page" % (len(entries)))
    return entries


##########
# MAIN
##########
def main():
    car_events = []
    grey_list = []

    # capture the the events from Eventbrite,
    # doing an initial pass on  filtering them
    # based on title into the white list or
    # grey list
    for url in SEARCH_URLS:
        print("Scanning", url)
        num = START_PAGE_NUM
        do_loop = True
        while do_loop and num < MAX_SEARCH_PAGES:
            html = get_page(url, num)
            if len(html.find_all(string=re.compile(r"Nothing matched"))) > 0:  # no more search results
                do_loop = False
            else:  # process the page for entries
                # (filter out just the car events )
                white_events, grey_events = filter_non_car(extract_entries(html))
                car_events.extend(white_events)
                grey_list.extend(grey_events)
                print('page - %i, %i possible events' % (num, len(white_events)))
                time.sleep(2)
                num += 1
        print("End of pages\n")
        print()

    # ... do a deeper check on grey items...
    print("2nd pass on grey items, checking their descriptions...(may take some time)")
    switch_from_grey = []
    for n, ev in enumerate(grey_list):
        event_id = ev["id"]
        description = get_description_body(event_id)
        w_score = white_score(description)
        b_score = black_score(description)
        print(n + 1, w_score, b_score, end=" ")
        if w_score > b_score and w_score >= WHITE_SCORE_THRESHOLD:
            switch_from_grey.append(ev)
            print("(found)")
        else:
            print()
    print()
    for ev in switch_from_grey:
        car_events.append(ev)
        grey_list.remove(ev)
    print("done 2nd pass.\n")

    if save_raw_dump:
        print("Saving 'raw_events.json'")
        # save for reference the data as is, in case we want to do additional work on them
        rawfile = open("raw_events.json", "w", encoding="utf-8")
        json.dump(car_events, rawfile)
        rawfile.close()

    # PROCESS CAR EVENTS
    # get rid of duplicates
    unique_events = {}
    for ev in car_events:
        unique_events[ev["id"]] = ev

    # convert to contracted json format
    print("converting and retrieving ticket info from Eventbrite on %i items...(may take a while)" % len(unique_events))
    converted = []
    for n, e in enumerate(unique_events.values()):
        converted.append(convert(e))
        print(n + 1)
    print()

    # save the converted events
    print("Saving %i scraped results as 'eventbrite_events.json'" % len(converted))
    event_file = open("eventbrite_events.json", "w", encoding="utf-8")
    json.dump(converted, event_file)
    event_file.close()
    print(len(converted), " events saved.\n")

    # PROCESS AND SAVE GREYIST EVENTS FOR REVIEW
    print("working on grey list...")
    unique_events = {}
    for ev in grey_list:
        unique_events[ev["id"]] = ev

    # convert to contracted json format
    print("converting and retrieving ticket info from Eventbrite. %i items...(may take a while)" % len(unique_events))
    converted = []
    for n, e in enumerate(unique_events.values()):
        converted.append(convert(e))
        print(n + 1, end=" ")
    print()

    # save the converted events
    print("Saving %i grey list results as 'grey_eventbrite_events.json'" % len(converted))
    grey_event_file = open("grey_eventbrite_events.json", "w", encoding="utf-8")
    json.dump(converted, grey_event_file)
    grey_event_file.close()
    print(len(converted), " events saved.\n")

    # save a list of just the names(for debugging)
    f = open("_event_names.txt", "w")
    for k in unique_events.keys():
        try:
            f.write(unique_events[k]["name"] + "\n")
        except:
            logging.info("problem saving name: %s", k)
    f.close()


if __name__ == "__main__":
    main()


