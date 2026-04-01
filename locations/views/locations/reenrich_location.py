from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views import View

from locations.models.Location import Location
from locations.services.location_geocoding import enrich_location, _address_is_hint
from locations.services.location_nearby import warn_nearby_duplicates


class ReEnrichLocationView(LoginRequiredMixin, PermissionRequiredMixin, View):
  """
  Staff-only action view that clears cached geo data and re-runs the full
  enrichment pipeline (address → coordinates → regions → place_id → phone).

  Intended use: fix wrong geo data after manually correcting the address.
  Accepts POST only; redirects to the location detail page when done.

  Address handling:
  - Real address (contains digits, e.g. "49 rue de Cîteaux, 21700 Agencourt"):
    kept as-is; only geo/place_id are cleared and re-fetched.
  - Hint address (no digits, e.g. "France" or "Gelderland"):
    cleared and passed to enrich_location as address_hint so Google
    can resolve the full formatted address.
  """
  permission_required = 'locations.delete_location'

  def post(self, request, slug):
    location = get_object_or_404(Location, slug=slug)
    address = location.address or None

    if address and not _address_is_hint(address):
      # Real address — keep it; only wipe the auto-populated geo fields.
      Location.objects.filter(pk=location.pk).update(
        google_place_id=None,
        geo=None,
        distance_to_departure_center=None,
      )
      location.google_place_id = None
      location.geo = None
      location.distance_to_departure_center = None
      enrich_location(location, request=request)
    else:
      # Hint address (or no address) — clear it so Google can resolve
      # the full formatted address from the location name + hint.
      Location.objects.filter(pk=location.pk).update(
        address=None,
        google_place_id=None,
        geo=None,
        distance_to_departure_center=None,
      )
      location.address = None
      location.google_place_id = None
      location.geo = None
      location.distance_to_departure_center = None
      enrich_location(location, request=request, address_hint=address)

    location.calculate_distance_to_departure_center(request=request)
    warn_nearby_duplicates(location, request)
    return redirect(location.get_absolute_url())
