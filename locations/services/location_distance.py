from geopy import distance
from django.contrib import messages
from locations.utils.get_departure_coordinates import get_departure_coordinates
from django.utils.text import capfirst

def calculate_distance_to_departure_center(location, request=None):
  """
  Calculate and cache distance from departure center.
  
  Args:
    location: Location instance
    request: Optional request for user messages
  
  Returns:
    Distance in km or None if calculation failed
  """
  if not location.coord_lat or not location.coord_lon:
    # Try to geocode first
    if location.address:
      from locations.services.location_geocoding import geocode_location
      geocode_location(location, request=request)
    
    if not location.coord_lat or not location.coord_lon:
      location.distance_to_departure_center = None
      location.save(update_fields=['distance_to_departure_center'])
      return None
  
  try:
    departure_coords = get_departure_coordinates()
    if not departure_coords:
      if request:
        messages.error(request, capfirst("could not determine departure center coordinates"))
      return None
    
    calculated_distance = distance.distance(
      departure_coords,
      (location.coord_lat, location.coord_lon)
    )
    
    old_distance = location.distance_to_departure_center
    location.distance_to_departure_center = round(calculated_distance.km)
    
    if old_distance != location.distance_to_departure_center:
      location.save(update_fields=['distance_to_departure_center'])

      if request:
        messages.success(request, capfirst(f"distance to departure center set to {location.distance_to_departure_center} km."))

      # Trigger region recalculation
      if location.region:
        location.region.calculate_average_distance_to_center()

    return location.distance_to_departure_center
    
  except Exception as e:
    if request:
      messages.error(request, capfirst(f"error calculating distance for {location.name}: {e}"))
    return None


def recalculate_all_distances(queryset=None, request=None):
  """
  Recalculate distances for multiple locations.
  
  Args:
    queryset: Location queryset (default: all with coordinates)
    request: Optional request for user messages
  
  Returns:
    dict with statistics
  """
  from locations.models import Location
  
  if queryset is None:
    queryset = Location.objects.filter(
      coord_lat__isnull=False,
      coord_lon__isnull=False
    )
  
  stats = {'calculated': 0, 'skipped': 0, 'failed': 0}
  
  for location in queryset:
    result = calculate_distance_to_departure_center(location, request=request)
    if result is not None:
      stats['calculated'] += 1
    elif location.coord_lat and location.coord_lon:
      stats['failed'] += 1
    else:
      stats['skipped'] += 1
  
  return stats