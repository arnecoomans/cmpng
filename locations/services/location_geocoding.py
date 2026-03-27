import logging
import googlemaps
from geopy.geocoders import GoogleV3
from geopy import exc as geopy_exc
from django.conf import settings
from django.contrib import messages
from django.utils.text import slugify

logger = logging.getLogger(__name__)

_ACCOMMODATION_TYPES = frozenset({
  'campground', 'rv_park', 'lodging', 'hotel', 'motel',
  'hostel', 'bed_and_breakfast',
})

_ACTIVITY_TYPES = frozenset({
  'tourist_attraction', 'amusement_park', 'aquarium', 'art_gallery',
  'museum', 'night_club', 'stadium', 'zoo', 'bowling_alley',
  'casino', 'spa', 'theme_park', 'gym',
})


def _get_geolocator():
  return GoogleV3(api_key=settings.GOOGLE_API_KEY)


def _get_gmaps_client():
  return googlemaps.Client(key=settings.GOOGLE_API_KEY)


def _geocode_raw(location, request=None, address_hint=None, use_name=True):
  """
  Internal helper: geocode and return the raw geopy result.
  Does NOT call fetch_address — callers are responsible for ensuring an address
  (or address_hint) is available before calling this.

  address_hint: optional override used as the geocode address context instead of
                location.address. Useful when the stored address has been cleared
                but the caller still wants to provide a search hint.
  use_name:     when True (default) prepend location.name to the query so Google
                can disambiguate ambiguous addresses.  Pass False when the address
                is already precise (street-level) — adding the name can shift the
                result to a different coordinate.

  Returns the geopy Location object, or None on failure.
  """
  addr = address_hint or location.address
  if not addr:
    if request:
      messages.warning(request, f"No address available to geocode '{location.name}'")
    return None

  query = f"{location.name}, {addr}" if use_name else addr
  logger.debug("geocode query: %r", query)
  try:
    result = _get_geolocator().geocode(query)
  except geopy_exc.GeocoderQueryError as e:
    logger.warning("geocode query error for %r: %s", location.name, e)
    if request:
      messages.error(request, f"Geocoding error for '{location.name}': {e}")
    return None
  except Exception as e:
    logger.warning("unexpected geocode error for %r: %s", location.name, e)
    msg = f"Unexpected geocoding error for '{location.name}'"
    if getattr(settings, 'DEBUG', False):
      msg += f": {e}"
    if request:
      messages.error(request, msg)
    return None

  if result:
    logger.debug(
      "geocode result for %r: lat=%.6f lon=%.6f place_id=%s",
      location.name, result.latitude, result.longitude,
      result.raw.get('place_id', '—'),
    )
  else:
    logger.info("geocode returned no result for query %r", query)
  return result


# ================================================================
# Step 1 — address from name
# ================================================================

def fetch_address(location, request=None):
  """
  Look up an address by searching Google with the location name.
  Skipped silently if location.address is already set.
  Saves location.address on success.

  Returns:
    address string, or None on failure / already set
  """
  if location.address:
    return location.address

  logger.debug("fetch_address query: %r", location.name)
  try:
    result = _get_geolocator().geocode(location.name)
  except geopy_exc.GeocoderQueryError as e:
    logger.warning("fetch_address query error for %r: %s", location.name, e)
    if request:
      messages.error(request, f"Error fetching address for '{location.name}': {e}")
    return None
  except Exception as e:
    logger.warning("fetch_address unexpected error for %r: %s", location.name, e)
    msg = f"Unexpected error fetching address for '{location.name}'"
    if getattr(settings, 'DEBUG', False):
      msg += f": {e}"
    if request:
      messages.error(request, msg)
    return None

  if result:
    logger.info("fetch_address: %r → %r", location.name, result.address)
    location.address = result.address
    location.save(update_fields=['address'])
    if request:
      messages.info(request, f"Found address for '{location.name}': {result.address}")
    return result.address

  logger.info("fetch_address: no result for %r", location.name)
  if request:
    messages.warning(request, f"No address found for '{location.name}'")
  return None


# ================================================================
# Step 2 — coordinates from address
# ================================================================

def geocode_location(location, request=None):
  """
  Geocode address → coordinates and save coord_lat / coord_lon.
  If no address is set, calls fetch_address() first.

  Returns:
    (lat, lon) tuple, or None on failure
  """
  result = _geocode_raw(location, request=request)
  if not result:
    if request and location.address:
      messages.warning(request, f"No geocoding result for '{location.name}'")
    return None

  location.coord_lat = result.latitude
  location.coord_lon = result.longitude
  location.save(update_fields=['coord_lat', 'coord_lon'])
  if request:
    messages.success(request, f"Coordinates set for '{location.name}': {result.latitude}, {result.longitude}")
  return (result.latitude, result.longitude)


# ================================================================
# Step 3 — geo regions from address components
# ================================================================

def _extract_address_parts(geocode_result):
  """
  Parse Google address_components into country / region / department.

  Priority order within each level means a more-specific type overrides
  a less-specific one (e.g. administrative_area_level_2 beats locality
  for department).

  Returns:
    dict with keys: country, country_slug, region, region_slug,
                    department, department_slug
  Raises:
    ValueError if country cannot be identified.
  """
  components = geocode_result.raw.get('address_components', [])
  if not components:
    raise ValueError("Google result has no address_components.")

  # Lower index = higher priority when multiple types match the same level.
  # First match wins for each target field.
  MAPPING = [
    ('country',                   'country',    'country_slug'),
    ('administrative_area_level_1','region',    'region_slug'),
    ('sublocality_level_1',        'region',    'region_slug'),
    ('administrative_area_level_2','department','department_slug'),
    ('administrative_area_level_3','department','department_slug'),
    ('locality',                   'department','department_slug'),
  ]

  result = {
    'country':         '(unknown)',
    'country_slug':    'xx',
    'region':          '(unknown region)',
    'region_slug':     'xx-region',
    'department':      '(unknown department)',
    'department_slug': 'xx-dept',
  }

  filled = set()
  for component in components:
    types      = component.get('types', [])
    long_name  = component.get('long_name', '')
    short_name = component.get('short_name', '')
    for google_type, target_name, target_slug in MAPPING:
      if google_type in types and target_name not in filled:
        result[target_name] = long_name
        result[target_slug] = short_name
        filled.add(target_name)

  if getattr(settings, 'DEBUG', False):
    missing = [k for k, v in result.items() if v.startswith('(')]
    if missing:
      print(f"[geocoding] Missing address fields: {', '.join(missing)}")

  if result['country'] == '(unknown)':
    raise ValueError(
      f"Could not identify country in Google address_components: "
      f"{[c.get('long_name') for c in components]}"
    )

  return result


def resolve_geo(location, geocode_result, request=None):
  """
  Resolve / create the Region hierarchy from a geocode result and
  assign the department-level Region to location.geo.
  Saves location.geo on success.

  Args:
    location:       Location instance
    geocode_result: geopy Location object (with .raw address_components)
    request:        Optional Django request for user-facing messages

  Returns:
    The department Region object, or None on failure.
  """
  from locations.models.Region import Region

  user = (request.user if request and request.user.is_authenticated else None) or location.user

  try:
    data = _extract_address_parts(geocode_result)
  except ValueError as e:
    if request:
      messages.warning(request, f"Could not resolve region for '{location.name}': {e}")
    return None

  defaults_base = {'status': 'p', 'visibility': 'p', 'user': user}

  country_obj, _ = Region.objects.get_or_create(
    slug=slugify(data['country_slug']),
    defaults={**defaults_base, 'name': data['country']},
  )
  region_obj, _ = Region.objects.get_or_create(
    slug=slugify(data['region_slug']),
    defaults={**defaults_base, 'name': data['region'], 'parent': country_obj},
  )
  department_obj, _ = Region.objects.get_or_create(
    slug=slugify(data['department_slug']),
    defaults={**defaults_base, 'name': data['department'], 'parent': region_obj},
  )

  location.geo = department_obj
  location.save(update_fields=['geo'])

  if request:
    messages.info(request, f"Region set for '{location.name}': {department_obj}")
  return department_obj


# ================================================================
# Orchestrator — run all enrichment steps in one API call
# ================================================================

def _geocode_result_has_street(geocode_result):
  """Return True if Google's result resolved to street level (has a street_number component)."""
  components = geocode_result.raw.get('address_components', [])
  return any('street_number' in c.get('types', []) for c in components)


def _address_is_hint(address):
  """
  Return True when the user's address looks like a search hint rather than a
  real address — i.e. it contains no digits.

  Examples:
    "nederland"           → True  (country hint)
    "Gelderland"          → True  (region hint)
    "Rijksstraatweg 1"    → False (has street number → real address)
    "75001 Paris"         → False (has postal code → real address)
  """
  return not any(c.isdigit() for c in (address or ''))


def _google_address_is_richer(user_address, google_address, min_ratio=1.5):
  """
  Return True if Google's address is at least min_ratio times longer than the
  user's input, indicating it added meaningful detail rather than just
  reformatting the same text.

  Example (min_ratio=1.5):
    user:   "nederland"        (9 chars)
    google: "Rijksstraatweg 1, 6744 PH Ederveen, Netherlands"  (48 chars)
    48 / 9 = 5.3 → True ✓

    user:   "Camping de Bron, France"  (23 chars)
    google: "Camping de Bron, 75000 Paris, France"  (37 chars)
    37 / 23 = 1.6 → True (borderline, but Google did add postal code + city)

    user:   "Rijksstraatweg 1, Ederveen"  (26 chars)
    google: "Rijksstraatweg 1, 6744 PH Ederveen, Netherlands"  (48 chars)
    → _address_is_hint returns False first, so this check is never reached
  """
  if not user_address:
    return True
  return len(google_address) >= len(user_address) * min_ratio


def _seed_types_from_google(location, geocode_result):
  """
  Set is_accommodation / is_activity on the location instance based on Google
  place types, but only when no categories are assigned yet.

  The values are set directly on the instance; the caller is responsible for
  saving them (or letting Location.save() / _update_types() persist them).

  Args:
    location:       Location instance
    geocode_result: geopy Location object with .raw['types']
  """
  if location.categories.exists():
    return

  google_types = set(geocode_result.raw.get('types', []))
  is_accommodation = bool(google_types & _ACCOMMODATION_TYPES)
  is_activity      = bool(google_types & _ACTIVITY_TYPES)

  # Fall back to accommodation when Google types are ambiguous
  if not is_accommodation and not is_activity:
    is_accommodation = True

  location.is_accommodation = is_accommodation
  location.is_activity      = is_activity


def fetch_phone(location):
  """
  Fetch and store the formatted phone number via Google Places Details API.
  Requires location.google_place_id to be set.
  No-op if phone is already set or place_id is missing.

  Returns:
    phone string, or None on failure / already set / no place_id
  """
  if location.phone or not location.google_place_id:
    return location.phone or None

  logger.debug("fetch_phone: %r (place_id=%s)", location.name, location.google_place_id)
  try:
    result = _get_gmaps_client().place(
      place_id=location.google_place_id,
      fields=['formatted_phone_number', 'international_phone_number'],
    )
  except Exception as e:
    logger.warning("fetch_phone failed for %r: %s", location.name, e)
    return None

  phone = (
    result.get('result', {}).get('formatted_phone_number')
    or result.get('result', {}).get('international_phone_number')
  )
  if phone:
    logger.info("fetch_phone: %r → %s", location.name, phone)
    location.phone = phone
    location.save(update_fields=['phone'])
  else:
    logger.info("fetch_phone: no phone in Places result for %r", location.name)
  return phone


def fetch_place_id(location):
  """
  Fetch and store Google place_id for a location if not already set.
  Uses a geocode query of 'name, address' and extracts the place_id from
  the raw result.  Saves location.google_place_id on success.

  Safe to call on existing locations with no place_id (e.g. batch backfill).
  No-op if google_place_id is already set.

  Returns:
    place_id string, or None on failure / already set
  """
  if location.google_place_id:
    return location.google_place_id

  logger.debug("fetch_place_id: %r", location.name)
  result = _geocode_raw(location)
  if not result:
    return None

  place_id = result.raw.get('place_id')
  if place_id:
    logger.info("fetch_place_id: %r → %s", location.name, place_id)
    location.google_place_id = place_id
    location.save(update_fields=['google_place_id'])
  else:
    logger.info("fetch_place_id: no place_id in result for %r", location.name)
  return place_id


def enrich_location(location, request=None, address_hint=None):
  """
  Full geocoding pipeline for a new location.
  Uses a single Google API call for steps 2, 3, and place_id.

    1. Fetch address from Google if missing  (fetch_address — 1 call)
    2. Geocode 'name, address' → coordinates (1 call, result reused for steps 3 & 4)
    2b. Overwrite address with Google's formatted address when the query was a hint.
        When address_hint is provided (re-enrichment), the street-level check is
        skipped — the caller has already decided the stored address should be replaced.
    3. Resolve address components → geo regions
    4. Store Google place_id (extracted from same result — no extra API call)

  Args:
    location:     Location instance
    request:      Optional Django request for user-facing messages
    address_hint: Optional address string to use as geocode context instead of
                  location.address. Pass when re-enriching after clearing the address.
  """
  # Step 1 — fetch address from Google if missing (skipped when address_hint is provided)
  if not address_hint and not location.address:
    fetch_address(location, request=request)

  # Use the address alone (no name prefix) when it is a precise street-level address.
  # Adding the name to a precise address can shift Google's result to a different coord.
  # Keep name+address for hint-based queries so Google can disambiguate.
  addr_for_check = address_hint if address_hint is not None else location.address
  use_name = _address_is_hint(addr_for_check)

  result = _geocode_raw(location, request=request, address_hint=address_hint, use_name=use_name)
  if not result:
    return

  # Step 2 — coordinates
  location.coord_lat = result.latitude
  location.coord_lon = result.longitude
  fields_to_save = ['coord_lat', 'coord_lon']

  # Step 2b — replace hint address with Google's full formatted address.
  # When address_hint is explicitly provided the street-level guard is relaxed:
  # the caller cleared the stored address on purpose, so any richer result wins.
  hint = address_hint if address_hint is not None else location.address
  street_ok = address_hint is not None or _geocode_result_has_street(result)
  if (
    _address_is_hint(hint)
    and street_ok
    and _google_address_is_richer(hint, result.address)
  ):
    location.address = result.address
    fields_to_save.append('address')
    if request:
      messages.info(request, f"Address updated from Google: {result.address}")

  # Step 4 — place_id (free, same result)
  place_id = result.raw.get('place_id')
  if place_id and not location.google_place_id:
    location.google_place_id = place_id
    fields_to_save.append('google_place_id')

  # Step 5 — seed is_accommodation / is_activity from Google types if no categories
  # (_update_types will preserve these values as long as no categories are assigned)
  _seed_types_from_google(location, result)

  location.save(update_fields=fields_to_save)
  if request:
    messages.success(request, f"Coordinates set for '{location.name}': {result.latitude}, {result.longitude}")

  # Step 3 — geo regions
  resolve_geo(location, result, request=request)

  # Step 6 — phone from Places Details (1 extra API call)
  if not location.phone and location.google_place_id:
    fetch_phone(location)


# ================================================================
# Batch geocoding
# ================================================================

def geocode_multiple_locations(queryset, request=None):
  """
  Geocode multiple locations in batch.

  Returns:
    dict with 'success', 'failed', 'skipped' counts
  """
  results = {'success': 0, 'failed': 0, 'skipped': 0}

  for location in queryset:
    if location.coord_lat and location.coord_lon:
      results['skipped'] += 1
      continue
    if not location.address:
      results['skipped'] += 1
      continue
    result = geocode_location(location, request=request)
    if result:
      results['success'] += 1
    else:
      results['failed'] += 1

  return results
