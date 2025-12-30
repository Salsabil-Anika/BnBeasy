from config import listings_collection
from bson.objectid import ObjectId

def get_listing_by_id(listing_id):
    """Retrieve a single listing by ID."""
    return listings_collection.find_one({"_id": ObjectId(listing_id)})

def update_listing(listing_id, update_data):
    """Update a listing by ID."""
    return listings_collection.update_one(
        {"_id": ObjectId(listing_id)},
        {"$set": update_data}
    )

def delete_listing(listing_id):
    """Delete a listing by ID."""
    return listings_collection.delete_one({"_id": ObjectId(listing_id)})

def add_listing(host_id, title, price, city, location, description, image_filename, amenities, latitude, longitude):
    listings_collection.insert_one({
        "host_id": host_id,
        "title": title,
        "price": price,
        "city": city,
        "location": location,
        "description": description,
        "image": image_filename,
        "amenities": amenities,
        "latitude": latitude,
        "longitude": longitude
    })

def create_listing(listing_data):
    """Inserts a listing dictionary into the database."""
    return listings_collection.insert_one(listing_data)

def extract_lat_lng_from_map_url(map_url):
    """
    Extracts latitude and longitude from a Google Maps URL.
    """
    match = re.search(r'/@([-.\\d]+),([-.\\d]+)', map_url)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def create_listing_from_args(
    host_id, name, description, price_per_night, amenities,
    location_city, space_type, has_coworking_space, photos,
    latitude, longitude
):
    """Creates a listing from individual arguments."""
    listing_data = {
        "host_id": host_id,
        "space_title": name,
        "description": description,
        "price_per_night": price_per_night,
        "amenities": amenities,
        "location_city": location_city,
        "space_type": space_type,
        "has_coworking_space": has_coworking_space,
        "photos": photos,
        "latitude": latitude,
        "longitude": longitude
    }
    return create_listing(listing_data)



def get_listings_by_host(host_id):
    """Retrieve all listings for a specific host."""
    return list(listings_collection.find({"host_id": host_id}))
