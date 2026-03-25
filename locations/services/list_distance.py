import googlemaps
from django.conf import settings
from django.utils.timezone import now


# ================================================================
# Internal helpers
# ================================================================

def _get_previous_location(list_item):
  """
  Return the Location that precedes list_item in its list.
  For the first item (order=0 or no prior item), returns the
  user's home location. Returns None if no home is set.
  """
  from locations.models import ListItem

  prev_item = (
    ListItem.objects
    .filter(list=list_item.list, order__lt=list_item.order)
    .select_related('location')
    .order_by('-order')
    .first()
  )
  if prev_item:
    return prev_item.location

  # Fall back to home location from list owner's preferences
  user = list_item.list.user
  if user and hasattr(user, 'preferences') and user.preferences.home:
    return user.preferences.home

  return None


def _fetch_from_google(origin, destination):
  """
  Call the Google Distance Matrix API for a single origin→destination pair.
  Returns (distance_m, duration_s) or raises on failure.

  Args:
    origin: Location instance with coord_lat / coord_lon
    destination: Location instance with coord_lat / coord_lon

  Returns:
    tuple[float, float]: (distance_m, duration_s)

  Raises:
    ValueError: if either location lacks coordinates or API returns no result
  """
  if not (origin.coord_lat and origin.coord_lon):
    raise ValueError(f"Origin '{origin}' has no coordinates.")
  if not (destination.coord_lat and destination.coord_lon):
    raise ValueError(f"Destination '{destination}' has no coordinates.")

  client = googlemaps.Client(key=settings.GOOGLE_API_KEY)
  result = client.distance_matrix(
    origins=[(float(origin.coord_lat), float(origin.coord_lon))],
    destinations=[(float(destination.coord_lat), float(destination.coord_lon))],
    mode='driving',
    units='metric',
  )

  try:
    element = result['rows'][0]['elements'][0]
    if element['status'] != 'OK':
      raise ValueError(f"Distance Matrix returned status: {element['status']}")
    distance_m  = float(element['distance']['value'])
    duration_s  = float(element['duration']['value'])
    return round(distance_m, 1), round(duration_s, 1)
  except (KeyError, IndexError) as e:
    raise ValueError(f"Unexpected Distance Matrix response: {e}")


# ================================================================
# Public API
# ================================================================

def get_or_fetch_distance(a, b, request=None):
  """
  Return a Distance record for locations a and b.
  Fetches from Google and stores it if not yet cached.

  Args:
    a: Location instance
    b: Location instance
    request: Optional request for Django messages

  Returns:
    Distance instance or None on failure
  """
  from locations.models import Distance
  from django.contrib import messages

  distance = Distance.get_for(a, b)
  if distance:
    return distance

  try:
    distance_m, duration_s = _fetch_from_google(a, b)
  except ValueError as e:
    if request:
      messages.error(request, str(e))
    return None

  origin, destination = Distance.normalize(a, b)
  distance, _ = Distance.objects.update_or_create(
    origin=origin,
    destination=destination,
    defaults={
      'distance_m':  distance_m,
      'duration_s':  duration_s,
      'cached_at':   now(),
    },
  )
  return distance


def resolve_leg(list_item, fetch=True, request=None):
  """
  Compute and store leg_distance for a single ListItem.

  Looks up (or fetches) the Distance between the previous location
  and this item's location, then saves it on the item.

  Args:
    list_item: ListItem instance
    fetch: If True, call Google API on cache miss. If False, only use cache.
    request: Optional request for Django messages

  Returns:
    Distance instance if resolved, None otherwise
  """
  prev = _get_previous_location(list_item)
  if prev is None or prev == list_item.location:
    return None

  if fetch:
    distance = get_or_fetch_distance(prev, list_item.location, request=request)
  else:
    from locations.models import Distance
    distance = Distance.get_for(prev, list_item.location)

  if distance and list_item.leg_distance_id != distance.pk:
    list_item.leg_distance = distance
    list_item.save(update_fields=['leg_distance'])

  return distance


def resolve_all_legs(trip_list, fetch=True, request=None):
  """
  Resolve leg_distance for every item in a list in order.

  Args:
    trip_list: List instance
    fetch: Passed through to resolve_leg
    request: Optional request for Django messages

  Returns:
    dict: {'resolved': int, 'failed': int}
  """
  stats = {'resolved': 0, 'failed': 0}
  for item in trip_list.items.select_related('location', 'leg_distance').order_by('order'):
    result = resolve_leg(item, fetch=fetch, request=request)
    if result:
      stats['resolved'] += 1
    else:
      stats['failed'] += 1
  return stats


def on_item_saved(list_item, request=None):
  """
  Call after adding or changing a ListItem's location or order.
  Resolves this item's leg and invalidates the next item's leg
  (since its previous location may have changed).

  Args:
    list_item: ListItem instance
    request: Optional request for Django messages
  """
  from locations.models import ListItem

  resolve_leg(list_item, request=request)

  next_item = (
    ListItem.objects
    .filter(list=list_item.list, order__gt=list_item.order)
    .order_by('order')
    .first()
  )
  if next_item:
    resolve_leg(next_item, request=request)


def on_item_deleted(trip_list, deleted_order, request=None):
  """
  Call after deleting a ListItem.
  Resolves the leg for the item that now follows the gap.

  Args:
    trip_list: List instance the item belonged to
    deleted_order: The order value of the deleted item
    request: Optional request for Django messages
  """
  from locations.models import ListItem

  next_item = (
    ListItem.objects
    .filter(list=trip_list, order__gt=deleted_order)
    .order_by('order')
    .first()
  )
  if next_item:
    resolve_leg(next_item, request=request)
