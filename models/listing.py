# models\listing.py
# Ei file ta listing (jemn: apartment, room) toiri, update, delete, ebong khujar kaaj kore.

import os
from pymongo import ASCENDING, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime
import re
# We need to create sample hosts, so we need access to the users collection and password hashing
from config import db, users_collection, listings_collection
from werkzeug.security import generate_password_hash


try:
    listings_collection.create_index([("price_per_night", ASCENDING)])
    listings_collection.create_index([("location_city", ASCENDING)])
    listings_collection.create_index([("has_coworking_space", ASCENDING)])
    print("Listing Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Listing Model: Error initializing listings collection: {e}")


# --- Core CRUD & Filter Functions ---

def create_listing(listing_data):
    """Database e ekta notun listing toiri kore ebong save kore."""
    listing_data["created_at"] = datetime.utcnow()
    return listings_collection.insert_one(listing_data)

def get_listing_by_id(listing_id):
    """Ekta nirdishto listing ke tar unique ID diye database theke fetch kore."""
    try:
        return listings_collection.find_one({"_id": ObjectId(listing_id)})
    except Exception:
        return None

def update_listing(listing_id, data):
    """Ekta listing er information update kore."""
    return listings_collection.update_one(
        {"_id": ObjectId(listing_id)},
        {"$set": data}
    )

def delete_listing(listing_id):
    """Ekta listing ke database theke delete kore."""
    return listings_collection.delete_one({"_id": ObjectId(listing_id)})

def get_all_listings():
    """Database theke shob listing fetch kore."""
    return list(listings_collection.find().sort("created_at", DESCENDING))

def get_listings_by_host(host_id):
    """Ekjon nirdishto host er toiri kora shob listing fetch kore."""
    return list(listings_collection.find({"host_id": host_id}).sort("created_at", DESCENDING))


def filter_listings(filters, user_profile=None):
    """Bivinno criteria'r upor base kore listing filter kore."""
    query = {}
    
    # Text search for location
    if filters.get('location'):
        query['location_city'] = re.compile(filters['location'], re.IGNORECASE)
        
    # Price range filter
    min_price = filters.get('min_price')
    max_price = filters.get('max_price')
    if min_price or max_price:
        price_query = {}
        if min_price:
            try:
                price_query['$gte'] = int(min_price)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                price_query['$lte'] = int(max_price)
            except (ValueError, TypeError):
                pass
        if price_query:
            query['price_per_night'] = price_query
    
    # Co-working space filter
    if filters.get('coworking'):
        query['has_coworking_space'] = True
        
    # Space type filter
    if filters.get('space_type'):
        query['space_type'] = filters['space_type']
        
    # Amenities filter (match all selected amenities)
    if filters.get('amenities'):
        query['amenities'] = {'$all': filters['amenities']}
    
    # Filter by a specific host
    if filters.get('host_id'):
        query['host_id'] = filters['host_id']

    # Find matching listings
    listings = list(listings_collection.find(query))

    # Sort results
    sort_by = filters.get('sort_by')
    if sort_by == 'price_asc':
        listings.sort(key=lambda x: x['price_per_night'])
    elif sort_by == 'price_desc':
        listings.sort(key=lambda x: x['price_per_night'], reverse=True)
    elif sort_by == 'best_match' and user_profile:
        # 'Best Match' sorting logic
        def calculate_score(listing):
            score = 0
            # Budget match
            if listing['price_per_night'] <= user_profile.get('max_budget', 99999):
                score += 20
            # Wifi speed match
            if listing.get('wifi_speed_mbps', 0) >= user_profile.get('min_wifi_speed', 0):
                score += 15
            # Location preference could be added here if we stored it
            return score
        
        listings.sort(key=calculate_score, reverse=True)
        
    return listings

def get_popular_listings_in_location(location, limit=4, exclude_id=None):
    """
    Finds other popular listings in the same location, excluding the current one.
    """
    query = {"location_city": location}
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    # Popularity can be defined by reviews, bookings, etc.
    # For now, we'll just get other listings from the same location.
    return list(listings_collection.find(query).limit(limit))


# --- Sample data utilities ---

def _picsum(seed: str, w: int = 800, h: int = 600):
    """Sample chobi generate korar jonno helper function."""
    # Using a different placeholder service as picsum can be unreliable with seeds
    return [
        f"https://placehold.co/{w}x{h}/1f2937/46e0c1?text={seed.replace('-', '%20')}-1",
        f"https://placehold.co/{w}x{h}/1f2937/46e0c1?text={seed.replace('-', '%20')}-2",
        f"https://placehold.co/{w}x{h}/1f2937/46e0c1?text={seed.replace('-', '%20')}-3",
    ]

def get_or_create_all_sample_hosts(sample_data):
    """
    Ensures all hosts from the sample data exist in the database and
    returns a mapping from their user_id (e.g., "nomad#1") to their real MongoDB _id.
    """
    host_map = {}
    
    # Extract unique hosts from the sample data
    unique_hosts = {d["host_id"]: d for d in sample_data}.values()

    for host_details in unique_hosts:
        user_id = host_details["host_id"]
        email = host_details["host_email"]
        
        host = users_collection.find_one({"user_id": user_id})
        if host:
            host_map[user_id] = str(host["_id"])
        else:
            # If not, create the host
            new_host = {
                "user_id": user_id,
                "first_name": host_details["host_name"].split(" ")[0],
                "last_name": " ".join(host_details["host_name"].split(" ")[1:]),
                "email": email,
                "nid": host_details["host_nid"],
                "phone": host_details["host_phone"],
                "password": generate_password_hash("password123"),
                "role": "host",
                "verification": {"status": "approved"},
                "is_verified": True,
                "created_at": datetime.utcnow(),
            }
            result = users_collection.insert_one(new_host)
            host_map[user_id] = str(result.inserted_id)
            print(f"Created sample host: {host_details['host_name']}")
    
    return host_map


def add_sample_listings():
    """Jodi database e kono listing na thake, tahole kichu sample data add kore."""
    if listings_collection.count_documents({}) == 0:
        print("No listings found. Adding 26 sample listings...")
        sample_data = [
            # Dhaka (3)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Gulshan Modern Apartment", "description": "A stylish apartment in the heart of Gulshan with all modern amenities.", "location_city": "Dhaka", "latitude": 23.7925, "longitude": 90.4078, "price_per_night": 3500, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC", "Kitchen", "Pool"], "wifi_speed_mbps": 150, "photos": _picsum("gulshan-modern"), "created_at": datetime.utcnow(), "map_url": "https://www.google.com/maps?q=23.7925,90.4078"},
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Dhanmondi Lake View Room", "description": "Private room with a beautiful view of Dhanmondi Lake.", "location_city": "Dhaka", "latitude": 23.7465, "longitude": 90.3760, "price_per_night": 1500, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["AC", "Kitchen"], "wifi_speed_mbps": 50, "photos": _picsum("dhanmondi-lake"), "created_at": datetime.utcnow()},
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Banani Shared Workspace", "description": "A budget-friendly shared room for students and backpackers.", "location_city": "Dhaka", "latitude": 23.7925, "longitude": 90.4078, "price_per_night": 800, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["High-Speed WiFi", "Kitchen"], "wifi_speed_mbps": 100, "photos": _picsum("banani-shared"), "created_at": datetime.utcnow()},

            # Chittagong (3)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Agrabad Business Suite", "description": "Private room perfect for business travelers.", "location_city": "Chittagong", "latitude": 22.3333, "longitude": 91.8333, "price_per_night": 2000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 80, "photos": _picsum("agrabad-suite"), "created_at": datetime.utcnow()},
            {"host_id": "ctg03", "host_name": "Rina Das", "host_email": "rina@email.com", "host_phone": "01711112222", "host_nid": "1993030303030", "space_title": "GEC Circle Cozy Room", "description": "A small and cozy room in the GEC Circle area.", "location_city": "Chittagong", "latitude": 22.3592, "longitude": 91.8217, "price_per_night": 1100, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["AC"], "wifi_speed_mbps": 45, "photos": _picsum("gec-circle"), "created_at": datetime.utcnow()},

            # Cox's Bazar (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Sea Pearl Shared Room", "description": "Affordable shared room with a direct view of the beach.", "location_city": "Cox's Bazar", "latitude": 21.4272, "longitude": 92.0058, "price_per_night": 1000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["AC"], "wifi_speed_mbps": 30, "photos": _picsum("cox-sea-pearl"), "created_at": datetime.utcnow()},
            {"host_id": "cox02", "host_name": "Jannat Ferdous", "host_email": "jannat@email.com", "host_phone": "01812345678", "host_nid": "1991010101010", "space_title": "Inani Beach House", "description": "A full beach house right on Inani Beach.", "location_city": "Cox's Bazar", "latitude": 21.2222, "longitude": 92.0425, "price_per_night": 5000, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking", "High-Speed WiFi"], "wifi_speed_mbps": 70, "photos": _picsum("inani-beach"), "created_at": datetime.utcnow()},

            # Sylhet (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Jaflong Nature Retreat", "description": "A peaceful private room surrounded by nature.", "location_city": "Sylhet", "latitude": 25.1639, "longitude": 92.0144, "price_per_night": 1300, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 25, "photos": _picsum("jaflong-retreat"), "created_at": datetime.utcnow()},
            {"host_id": "syl03", "host_name": "Peter Das", "host_email": "peter@email.com", "host_phone": "01612345678", "host_nid": "1988080808080", "space_title": "Zindabazar Apartment", "description": "An apartment in the busiest part of Sylhet.", "location_city": "Sylhet", "latitude": 24.8949, "longitude": 91.8687, "price_per_night": 2200, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC", "Kitchen"], "wifi_speed_mbps": 100, "photos": _picsum("zindabazar"), "created_at": datetime.utcnow()},

            # Sreemangal (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Sreemangal Tea Estate Bungalow", "description": "An entire bungalow inside a tea garden.", "location_city": "Sreemangal", "latitude": 24.3069, "longitude": 91.7292, "price_per_night": 4000, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "Kitchen", "Parking"], "wifi_speed_mbps": 60, "photos": _picsum("sreemangal-bungalow"), "created_at": datetime.utcnow()},
            {"host_id": "syl04", "host_name": "Nisha Deb", "host_email": "nisha@email.com", "host_phone": "01511223344", "host_nid": "1995050505050", "space_title": "Lawachara Forest Cabin", "description": "A rustic cabin on the edge of Lawachara National Park.", "location_city": "Sreemangal", "latitude": 24.3167, "longitude": 91.7833, "price_per_night": 1800, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 20, "photos": _picsum("lawachara-cabin"), "created_at": datetime.utcnow()},

            # Khulna (2)
            {"host_id": "khl01", "host_name": "Mizanur Rahman", "host_email": "mizanur@email.com", "host_phone": "01199999999", "host_nid": "1987060606060", "space_title": "Sundarbans Eco Hut", "description": "A rustic shared hut for nature lovers.", "location_city": "Khulna", "latitude": 22.8167, "longitude": 89.5500, "price_per_night": 700, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 20, "photos": _picsum("sundarbans-hut"), "created_at": datetime.utcnow()},
            {"host_id": "khl02", "host_name": "Afia Sultana", "host_email": "afia@email.com", "host_phone": "01987654321", "host_nid": "1990121212121", "space_title": "City Center Apartment", "description": "A modern apartment in the heart of Khulna.", "location_city": "Khulna", "latitude": 22.8153, "longitude": 89.5663, "price_per_night": 1800, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 90, "photos": _picsum("khulna-center"), "created_at": datetime.utcnow()},

            # Rajshahi (2)
            {"host_id": "raj01", "host_name": "Ayesha Siddika", "host_email": "ayesha@email.com", "host_phone": "01010101010", "host_nid": "1996070707070", "space_title": "Padma River View Apartment", "description": "Full apartment with a view of the Padma river.", "location_city": "Rajshahi", "latitude": 24.3667, "longitude": 88.6000, "price_per_night": 2200, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["AC", "Kitchen", "Parking"], "wifi_speed_mbps": 45, "photos": _picsum("padma-view"), "created_at": datetime.utcnow()},
            {"host_id": "raj02", "host_name": "Imran Mahmud", "host_email": "imran@email.com", "host_phone": "01711223344", "host_nid": "1985050505050", "space_title": "University Area Private Room", "description": "A quiet and clean private room near Rajshahi University.", "location_city": "Rajshahi", "latitude": 24.3745, "longitude": 88.6042, "price_per_night": 1200, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "Kitchen"], "wifi_speed_mbps": 60, "photos": _picsum("rajshahi-uni"), "created_at": datetime.utcnow()},
            
            # Barisal (2)
            {"host_id": "bar01", "host_name": "Farhan Islam", "host_email": "farhan@email.com", "host_phone": "01231231231", "host_nid": "1994080808080", "space_title": "Barisal City Center Room", "description": "A convenient private room in the city center.", "location_city": "Barisal", "latitude": 22.7010, "longitude": 90.3535, "price_per_night": 900, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 70, "photos": _picsum("barisal-center"), "created_at": datetime.utcnow()},
            {"host_id": "bar02", "host_name": "Shila Rani", "host_email": "shila@email.com", "host_phone": "01811223344", "host_nid": "1992020202020", "space_title": "Riverside Guesthouse", "description": "A guesthouse with a beautiful view of the river.", "location_city": "Barisal", "latitude": 22.7010, "longitude": 90.3535, "price_per_night": 1400, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 30, "photos": _picsum("barisal-river"), "created_at": datetime.utcnow()},

            # Rangpur (2)
            {"host_id": "ran01", "host_name": "Ishita Roy", "host_email": "ishita@email.com", "host_phone": "01451451451", "host_nid": "1997090909090", "space_title": "Rangpur Quiet Corner", "description": "A quiet shared room for focused work.", "location_city": "Rangpur", "latitude": 25.7439, "longitude": 89.2752, "price_per_night": 600, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["High-Speed WiFi"], "wifi_speed_mbps": 90, "photos": _picsum("rangpur-quiet"), "created_at": datetime.utcnow()},
            {"host_id": "ran02", "host_name": "Asif Iqbal", "host_email": "asif@email.com", "host_phone": "01911223344", "host_nid": "1990101010101", "space_title": "Modern Studio Apartment", "description": "A fully furnished studio apartment in Rangpur.", "location_city": "Rangpur", "latitude": 25.7439, "longitude": 89.2752, "price_per_night": 1600, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["AC", "Kitchen", "High-Speed WiFi"], "wifi_speed_mbps": 80, "photos": _picsum("rangpur-studio"), "created_at": datetime.utcnow()},

            # Mymensingh (2)
            {"host_id": "mym01", "host_name": "Rashed Kabir", "host_email": "rashed@email.com", "host_phone": "01671671671", "host_nid": "1986101010101", "space_title": "Brahmaputra Riverside Apartment", "description": "Enjoy the view of the Brahmaputra river.", "location_city": "Mymensingh", "latitude": 24.7471, "longitude": 90.4203, "price_per_night": 1600, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 35, "photos": _picsum("brahmaputra-apt"), "created_at": datetime.utcnow()},
            {"host_id": "mym02", "host_name": "Farida Yasmin", "host_email": "farida@email.com", "host_phone": "01311223344", "host_nid": "1989090909090", "space_title": "Agricultural University Guest Room", "description": "A private room for visitors to the Agricultural University.", "location_city": "Mymensingh", "latitude": 24.7269, "longitude": 90.4325, "price_per_night": 950, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi"], "wifi_speed_mbps": 55, "photos": _picsum("mymensingh-uni"), "created_at": datetime.utcnow()},

            # Gazipur (2)
            {"host_id": "gaz01", "host_name": "Tania Rahman", "host_email": "tania@email.com", "host_phone": "01987654321", "host_nid": "1993111111111", "space_title": "Gazipur Industrial Hub Room", "description": "Private room for professionals working in Gazipur.", "location_city": "Gazipur", "latitude": 24.0958, "longitude": 90.4125, "price_per_night": 1100, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC", "Parking"], "wifi_speed_mbps": 110, "photos": _picsum("gazipur-hub"), "created_at": datetime.utcnow()},
            {"host_id": "gaz02", "host_name": "Karim Sheikh", "host_email": "karim@email.com", "host_phone": "01712345678", "host_nid": "1984040404040", "space_title": "Bhawal National Park Resthouse", "description": "A quiet resthouse near Bhawal National Park.", "location_city": "Gazipur", "latitude": 24.0958, "longitude": 90.4125, "price_per_night": 2000, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 30, "photos": _picsum("bhawal-park"), "created_at": datetime.utcnow()},

            # Bandarban (2)
            {"host_id": "ban01", "host_name": "David Tripura", "host_email": "david.t@email.com", "host_phone": "01515151515", "host_nid": "1999030303030", "space_title": "Bandarban Hillside Cabin", "description": "A rustic shared cabin with breathtaking views.", "location_city": "Bandarban", "latitude": 22.1994, "longitude": 92.2185, "price_per_night": 1500, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 15, "photos": _picsum("bandarban-cabin"), "created_at": datetime.utcnow()},
            {"host_id": "ban02", "host_name": "Maria Marma", "host_email": "maria@email.com", "host_phone": "01812345678", "host_nid": "1998080808080", "space_title": "Nilgiri Mountain View", "description": "A room with a stunning view of the Nilgiri mountains.", "location_city": "Bandarban", "latitude": 21.9558, "longitude": 92.3236, "price_per_night": 2500, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Parking"], "wifi_speed_mbps": 10, "photos": _picsum("nilgiri-view"), "created_at": datetime.utcnow()},
        ]
        
        # Get a map of user_id -> real _id
        host_id_map = get_or_create_all_sample_hosts(sample_data)
        
        # Replace placeholder host_id with real _id
        for listing in sample_data:
            placeholder_id = listing["host_id"]
            if placeholder_id in host_id_map:
                listing["host_id"] = host_id_map[placeholder_id]
            # Remove extra host details not part of the listing schema
            for key in ["host_name", "host_email", "host_phone", "host_nid"]:
                if key in listing:
                    del listing[key]

        listings_collection.insert_many(sample_data)
        print(f"{len(sample_data)} sample listings added.")


def reset_sample_data():
    """Deletes and re-inserts sample data for testing."""
    deleted = listings_collection.delete_many({}).deleted_count
    print(f"Deleted {deleted} existing listings. Reinserting samples...")
    add_sample_listings()

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

