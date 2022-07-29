scape.py - scrapes the Eventbrite site for car related events

Dependencies:
    - a developer api key from Eventbrite, it needs to be saved in a file called "eventbrite_api_key.txt"
    - requires the Requests and BeautifulSoup python libraries

Usage:
    python scrape.py

Output:
    a json file called 'eventbrite_events.json' where the format is the following:

/* output of the scraper is a json list of Event objects

i.e [ EventObject, EventObject, ...]

where an EventObject is:
*/

{
"name"              : "Event Name",
"summary"           : "A description",
"startDatetime"     : "UTC formatted datetime",

"startDatetimeLocal" : "local start time",
"endDatetime"       : "UTC formatted datetime",
"endDatetimeLocal" : "local end time",
"url"               : "If available, a public url to the event",
"venue_name"        : "Location name",
"venue_address"     : "Street number and name",
"venue_city"        : "City",
"venue_region"      : "State/province/etc.",
"venue_country"     : "US/Canada/etc."
"venue_code"        : "ZIP/postal code/etc",

    
}



