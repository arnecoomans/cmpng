import hashlib

from django.core.cache import cache
from django.conf import settings
from geopy.geocoders import GoogleV3
from geopy import distance


def get_departure_coordinates():
    """
    Get departure center coordinates with caching.
    Returns (latitude, longitude) tuple or None.
    """
    key_hash = hashlib.md5(settings.DEPARTURE_CENTER.encode()).hexdigest()
    cache_key = f'departure_coords_{key_hash}'
    coords = cache.get(cache_key)
    
    if coords:
        return coords
    
    # Geocode and cache for 30 days
    try:
        geolocator = GoogleV3(api_key=settings.GOOGLE_API_KEY)
        departure = geolocator.geocode(settings.DEPARTURE_CENTER)
        
        if departure:
            coords = (departure.latitude, departure.longitude)
            cache.set(cache_key, coords, 60 * 60 * 24 * 30)  # 30 days
            return coords
    except Exception:
        pass
    
    return None