from flask import render_template, request
from . import traveller_bp
import os


@traveller_bp.route('/home')
def home():
    """Render traveller home using `models.space` data so detail links match space IDs."""
    listings = []
    try:
        from models.space import filter_spaces

        filters = {}
        city = request.args.get('city')
        if city:
            filters['location'] = city
        price = request.args.get('price')
        if price:
            filters['max_price'] = price
        filters['amenities'] = request.args.getlist('amenities')

        spaces = filter_spaces(filters)

        # Normalize spaces into the `listing` shape expected by the template
        for s in spaces:
            photo = None
            photos = s.get('photos') or []
            if photos:
                first = photos[0]
                # if stored as uploads/<name> or absolute path, keep basename
                if isinstance(first, str) and ('/' in first):
                    photo = os.path.basename(first)
                else:
                    photo = first

            listings.append({
                '_id': str(s.get('_id')),
                'title': s.get('space_title'),
                'image': photo,
                'price': s.get('price_per_night'),
                'city': s.get('location_city'),
                'location': s.get('location_city'),
                'amenities': s.get('amenities', [])
            })
    except Exception:
        listings = []

    return render_template('traveller/home.html', listings=listings)
