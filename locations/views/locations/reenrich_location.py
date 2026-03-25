from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views import View

from locations.models.Location import Location
from locations.services.location_geocoding import enrich_location


class ReEnrichLocationView(LoginRequiredMixin, View):
  """
  Staff-only action view that clears cached geo data and re-runs the full
  enrichment pipeline (address → coordinates → regions → place_id → phone).

  Intended use: fix wrong geo data after manually correcting the address.
  Accepts POST only; redirects to the location detail page when done.
  """

  def dispatch(self, request, *args, **kwargs):
    if not request.user.is_staff:
      location = get_object_or_404(Location, slug=kwargs.get('slug'))
      messages.warning(request, capfirst(_('action not allowed.')))
      return redirect(location.get_absolute_url())
    return super().dispatch(request, *args, **kwargs)

  def post(self, request, slug):
    location = get_object_or_404(Location, slug=slug)

    # Preserve the address as a search hint, then wipe all auto-populated fields
    # so the pipeline runs completely from scratch (bypasses Location.save() hooks).
    address_hint = location.address or None
    Location.objects.filter(pk=location.pk).update(
      address=None,
      google_place_id=None,
      geo=None,
    )
    location.address = None
    location.google_place_id = None
    location.geo = None

    enrich_location(location, request=request, address_hint=address_hint)
    return redirect(location.get_absolute_url())
