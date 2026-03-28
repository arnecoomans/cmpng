import math
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.utils.text import capfirst
from django.utils.translation import gettext as _

PROXIMITY_RADIUS_KM = 0.5


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
  """Return great-circle distance in km between two (lat, lon) points."""
  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  dphi = math.radians(lat2 - lat1)
  dlambda = math.radians(lon2 - lon1)
  a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
  return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bounding_box(queryset, lat, lon, radius_km):
  """
  Pre-filter queryset to a bounding box before exact haversine calculation.

  1 degree latitude  ≈ 111 km (constant).
  1 degree longitude ≈ 111 km × cos(lat) (shrinks toward poles).

  The bounding box slightly over-selects (corners are further than radius_km),
  so the Python haversine pass below removes the false positives.
  """
  lat_delta = radius_km / 111.0
  lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
  return queryset.filter(
    coord_lat__range=(lat - lat_delta, lat + lat_delta),
    coord_lon__range=(lon - lon_delta, lon + lon_delta),
  )


def get_nearby_locations(location, radius_km=None, queryset=None):
  """
  Return Location instances within radius_km, sorted by distance ascending.

  Each returned instance has a .nearby_distance attribute (float, km, 1 decimal).

  Strategy — SQLite and PostgreSQL (no PostGIS):
    1. Bounding box SQL filter  → eliminates obviously-far rows cheaply.
    2. Python haversine          → exact distance, removes bounding-box corners.
    3. Sort in Python            → by distance ascending.

  PostgreSQL + PostGIS upgrade path (swap only this function's internals):
    point = Point(lon, lat, srid=4326)
    return (
      queryset
        .exclude(pk=location.pk)
        .annotate(nearby_distance=Distance('point_field', point))
        .filter(nearby_distance__lte=D(km=radius_km))
        .order_by('nearby_distance')
    )

  Args:
    location:   Location instance. Must have coord_lat and coord_lon.
    radius_km:  Search radius in km. Falls back to settings.NEARBY_RANGE or 50.
    queryset:   Optional pre-filtered base queryset (e.g. already filtered by
                visibility, type, or user). Defaults to published locations.

  Returns:
    List[Location] sorted by distance. Empty list if location has no coordinates.
  """
  from locations.models import Location

  radius_km = float(radius_km or getattr(settings, 'NEARBY_RANGE', 50))

  if not location.coord_lat or not location.coord_lon:
    return []

  lat = float(location.coord_lat)
  lon = float(location.coord_lon)

  if queryset is None:
    queryset = Location.objects.filter(status='p')

  candidates = (
    queryset
    .exclude(pk=location.pk)
    .filter(coord_lat__isnull=False, coord_lon__isnull=False)
  )
  candidates = _bounding_box(candidates, lat, lon, radius_km)

  results = []
  for loc in candidates:
    dist = haversine_km(lat, lon, float(loc.coord_lat), float(loc.coord_lon))
    if dist <= radius_km:
      loc.nearby_distance = round(dist, 1)
      results.append(loc)

  results.sort(key=lambda loc: loc.nearby_distance)
  return results


def warn_nearby_duplicates(location, request):
  """Add a warning message if other locations exist within PROXIMITY_RADIUS_KM.

  Checks all published locations plus the requesting user's own locations
  across all statuses. Safe to call when coordinates are not yet set —
  returns silently in that case.

  Args:
    location: Location instance (must already have coord_lat/coord_lon set).
    request:  HttpRequest — used for scoping and attaching the message.
  """
  if not location.coord_lat or not location.coord_lon:
    return
  nearby_qs = location.__class__.objects.filter(
    Q(status='p') | Q(user=request.user)
  )
  nearby = get_nearby_locations(location, radius_km=PROXIMITY_RADIUS_KM, queryset=nearby_qs)
  if not nearby:
    return

  def _linked(loc):
    url = loc.get_absolute_url() if loc.status == 'p' else None
    return f'<a href="{url}">{loc.name}</a>' if url else loc.name

  parts = [_linked(loc) for loc in nearby[:3]]
  if len(nearby) > 3:
    parts.append(_(' and {} more').format(len(nearby) - 3))
  names = ', '.join(parts)
  messages.warning(
    request,
    capfirst(_('this location is very close to: %(names)s. Is this a duplicate?') % {'names': names}),
  )
