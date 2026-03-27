from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views import View

from locations.models.Location import Location
from locations.services.location_geocoding import enrich_location, _address_is_hint


class ReEnrichLocationView(LoginRequiredMixin, View):
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

  def dispatch(self, request, *args, **kwargs):
    if not request.user.is_staff:
      location = get_object_or_404(Location, slug=kwargs.get('slug'))
      messages.warning(request, capfirst(_('action not allowed.')))
      return redirect(location.get_absolute_url())
    return super().dispatch(request, *args, **kwargs)

  def post(self, request, slug):
    location = get_object_or_404(Location, slug=slug)
    address = location.address or None

    if address and not _address_is_hint(address):
      # Real address — keep it; only wipe the auto-populated geo fields.
      Location.objects.filter(pk=location.pk).update(
        google_place_id=None,
        geo=None,
      )
      location.google_place_id = None
      location.geo = None
      enrich_location(location, request=request)
    else:
      # Hint address (or no address) — clear it so Google can resolve
      # the full formatted address from the location name + hint.
      Location.objects.filter(pk=location.pk).update(
        address=None,
        google_place_id=None,
        geo=None,
      )
      location.address = None
      location.google_place_id = None
      location.geo = None
      enrich_location(location, request=request, address_hint=address)

    return redirect(location.get_absolute_url())
