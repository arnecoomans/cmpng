from django.views.generic import DetailView
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect, render

from locations.models.Location import Location
from django.utils.translation import gettext as _
from django.utils.text import capfirst
# from django.urls import reverse_lazy, reverse
from django.conf import settings
# from django.utils.html import escape
# from django.db.models import F, FloatField, IntegerField, Value
# from django.db.models.functions import Coalesce
from cmnsd.mixins import RequestMixin, FilterMixin

from math import floor, ceil

from locations.models.Location import Location, Region, Category, Tag
from cmnsd.mixins import RequestMixin, FilterMixin

class LocationDetailView(RequestMixin, FilterMixin, DetailView):
  model = Location
  template_name = 'locations/location_detail.html'
  context_object_name = 'location'
  
  def dispatch(self, request, *args, **kwargs):
    try:
      return super().dispatch(request, *args, **kwargs)
    except PermissionDenied:
      if not request.user.is_authenticated:
        messages.warning(request, capfirst(_('this page is not available.') + ' ' + capfirst(_('you might need to log in to see this.'))))
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
      return render(request, 'errorpages/private.html', status=403)

  def get_queryset(self):
    return Location.objects.select_related(
      'geo', 'geo__parent', 'geo__parent__parent',
      'chain', 'chain__parent',
      'size',
    ).prefetch_related(
      'categories',
      'tags',
      'visitors',
      'favorited',
      'media',
      'links',
    )

  def get_object(self, queryset=None):
    location = super().get_object(queryset)
    if not location.is_visible_to(self.request.user):
      raise PermissionDenied
    return location

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    self.object.request = self.request  # needed for visibility-filtered methods (filtered_tags, ordered_media, etc.)
    context['filtered_media'] = self.object.ordered_media()
    context['scope'] = 'location'
    return context