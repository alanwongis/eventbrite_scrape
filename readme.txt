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

"_raw_data": {
    
    /* the raw data scraped from the site.
    For example, the some of the following
    comes from a scrape of an eventbrite 
    search entry */
    
    "id"                : "event id used for their API",
    "primary_venue_id"  : "venue id",
    "tickets_url"       : ""
    /* ...etc */
    
    
}



