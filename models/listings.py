from config import listings_collection

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
