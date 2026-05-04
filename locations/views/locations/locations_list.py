from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.conf import settings
from django.db.models import Q
from cmnsd.mixins import RequestMixin, FilterMixin

from math import floor, ceil
import re

from locations.models.Location import Location, Region, Category, Tag

class LocationListMasterView(RequestMixin, FilterMixin, ListView):
  model = Location
  template_name = 'locations/locations_list.html'
  context_object_name = 'locations'
  # paginate_by = settings.ITEMS_PER_PAGE

  def get(self, request, *args, **kwargs):
    if request.GET.get('format') == 'filters':
      return self._filters_json_response()
    return super().get(request, *args, **kwargs)

  _VIEWPORT_PARAMS = {'coord_lat__gte', 'coord_lat__lte', 'coord_lon__gte', 'coord_lon__lte'}

  def _filters_json_response(self):
    from django.http import JsonResponse
    # Keep viewport params so the queryset is filtered to the current map area
    with_viewport = self.request.GET.copy()
    with_viewport.pop('format', None)
    self.request.GET = with_viewport
    qs = self.get_queryset()
    base_qs = self._optimized_queryset
    # Strip viewport params before building option URLs (they must not appear in filter link hrefs)
    without_viewport = with_viewport.copy()
    for p in self._VIEWPORT_PARAMS:
      without_viewport.pop(p, None)
    self.request.GET = without_viewport
    cat = self.get_category_filter_options(qs)
    tag = self.get_tag_filter_options(qs)
    return JsonResponse({
      'category': {'options': cat.get('options', []), 'all_options': cat.get('all_options', [])},
      'tag': {'options': tag.get('options', []), 'all_options': tag.get('all_options', [])},
      'types': {
        'accommodations': base_qs.filter(is_accommodation=True).exists(),
        'activities': base_qs.filter(is_activity=True).exists(),
      },
    })

  def get_queryset(self):
    if not hasattr(self, '_optimized_queryset'):
      self._optimized_queryset = self.get_optimized_queryset()
    return self._optimized_queryset
  
  def get_optimized_queryset(self):
    # queryset = super().get_queryset()
    queryset = self.model.get_optimized_queryset()
    # Get the filter mapping from the model
    mapping = getattr(self.model, 'get_filter_mapping', lambda: {})()
    # Apply filters to the queryset
    queryset = self.filter(
      queryset,
      mapping=mapping,
      request=self.request,
      )
    # Check what extra statuses are available before applying the status filter
    self._check_extra_statuses(queryset)
    # Always include published; optionally include concept (user) and revoked (staff)
    status = ['p']
    if 'status' in self.get_search_data_for_context():
      status = self.get_search_data_for_context()['status']
    queryset = queryset.filter(status__in=status)

    queryset = queryset.with_visit_state(self.request.user)

    return queryset
  
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    if hasattr(self, 'get_search_data_for_context'):
      context['active_filters'] = self.get_search_data_for_context()
    context['available_filters'] = self.get_available_filters_for_context()
    for location in context['locations']:
      location.request = self.request
    return context
  
  def get_available_filters_for_context(self):
    limit = 0  # Set a reasonable limit for filter options to prevent performance issues
    min_usage = 1  # Only show filters that are used at least once in the current queryset
    # Get available filters based on the current queryset
    available_filters = {}
    # Geo: use get_geo_filter_options to fetch available geo filters based on the current queryset
    available_filters['geo'] = self.get_geo_filter_options(self.get_queryset())
    # Category: use get_category_filter_options to fetch available category filters based on the current queryset
    available_filters['category'] = self.get_category_filter_options(self.get_queryset(), limit=limit, min_usage=min_usage)
    # Tag: use get_tag_filter_options to fetch available tag filters based on the current queryset
    available_filters['tag'] = self.get_tag_filter_options(self.get_queryset(), limit=limit, min_usage=min_usage)
    # Visibility: use get_visibility_filter_options to fetch available visibility filters based on the current queryset
    available_filters['visibility'] = self.get_visibility_filter_options(self.get_queryset())
    # Status: extra statuses available to this user (concept, revoked)
    available_filters['status'] = self.get_status_filter_options()
    return available_filters


  def _check_extra_statuses(self, qs):
    user = self.request.user
    self._has_concept = user.is_authenticated and qs.filter(status='c', user=user).exists()
    self._has_revoked = user.is_staff and qs.filter(status='r').exists()

  def get_status_filter_options(self):
    if not hasattr(self, '_has_concept'):
      return []
    if not self._has_concept and not self._has_revoked:
      return []
    options = [{'key': 'p', 'label': str(_('published'))}]
    if self._has_concept:
      options.append({'key': 'c', 'label': str(_('my drafts'))})
    if self._has_revoked:
      options.append({'key': 'r', 'label': str(_('revoked'))})
    return options

  def get_geo_filter_options(self, qs):
    country_ids = qs.filter(geo__parent__parent__isnull=False).values_list('geo__parent__parent', flat=True).distinct()
    country_count = country_ids.count()
    if country_count > 1:
      options = list(Region.objects.filter(id__in=country_ids).order_by('name').values('id', 'slug', 'name'))
      return {'key': 'country', 'label': 'country', 'options': options}
    if country_count == 1:
      region_ids = qs.filter(geo__parent__isnull=False).values_list('geo__parent', flat=True).distinct()
      region_count = region_ids.count()
      if region_count > 1:
        options = list(Region.objects.filter(id__in=region_ids).order_by('name').values('id', 'slug', 'name'))
        return {'key': 'region', 'label': 'region', 'options': options}
      if region_count == 1:
        dept_ids = qs.filter(geo__isnull=False).values_list('geo', flat=True).distinct()
        if dept_ids.count() > 1:
          options = list(Region.objects.filter(id__in=dept_ids).order_by('name').values('id', 'slug', 'name'))
          return {'key': 'department', 'label': 'department', 'options': options}
    return {}

  def get_visibility_filter_options(self, qs):
    if not self.request.user.is_authenticated:
      return {}
    from cmnsd.models import VisibilityModel
    display_names = dict(VisibilityModel.visibility_choices)
    active_code = self.request.GET.get('visibility', '')
    codes = list(qs.values_list('visibility', flat=True).distinct().order_by('visibility'))
    if not codes:
      return {}
    if len(codes) == 1 and not active_code:
      return {'key': 'visibility', 'label': 'visibility', 'options': [], 'sole_name': str(display_names.get(codes[0], codes[0]))}
    options = []
    for code in codes:
      if code == active_code:
        continue
      params = self.request.GET.copy()
      params['visibility'] = code
      options.append({
        'key': code,
        'name': str(display_names.get(code, code)),
        'url': self.request.path + '?' + params.urlencode(),
      })
    if not options and not active_code:
      return {}
    result = {'key': 'visibility', 'label': 'visibility', 'options': options}
    if active_code:
      result['active_name'] = str(display_names.get(active_code, active_code))
    return result

  def get_category_filter_options(self, qs, limit=10, min_usage=1):
    raw = self.request.GET.get('category', '')
    active_slugs = set(s for s in re.split(r'__and__|&&|,', raw) if s)
    categories_qs = Location.get_categories_from_queryset(qs, limit=limit, min_usage=min_usage)
    base_params = self.request.GET.copy()
    options = []
    all_options = []
    for c in categories_qs:
      all_options.append({'name': c['name'], 'slug': c['slug']})
      if c['slug'] in active_slugs:
        continue
      params = base_params.copy()
      existing = [s for s in re.split(r'__and__|&&|,', params.get('category', '')) if s]
      existing.append(c['slug'])
      params['category'] = '__and__'.join(existing)
      c = dict(c)
      c['url'] = self.request.path + '?' + params.urlencode()
      options.append(c)
    return {'key': 'category', 'label': 'categories', 'options': options, 'all_options': all_options}

  def get_tag_filter_options(self, qs, limit=10, min_usage=1):
    raw = self.request.GET.get('tag', '')
    active_slugs = set(s for s in re.split(r'__and__|&&|,', raw) if s)
    tags_qs = Location.get_tags_from_queryset(qs, limit=limit, min_usage=min_usage)
    base_params = self.request.GET.copy()
    options = []
    all_options = []
    for t in tags_qs:
      all_options.append({'name': t['name'], 'slug': t['slug']})
      if t['slug'] in active_slugs:
        continue
      params = base_params.copy()
      existing = [s for s in re.split(r'__and__|&&|,', params.get('tag', '')) if s]
      existing.append(t['slug'])
      params['tag'] = '__and__'.join(existing)
      t = dict(t)
      t['url'] = self.request.path + '?' + params.urlencode()
      options.append(t)
    return {'key': 'tag', 'label': 'tags', 'options': options, 'all_options': all_options}

class AllLocationListView(LocationListMasterView):
  def get_queryset(self):
    queryset = super().get_queryset()
    # No additional filtering needed for all locations
    return queryset
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'all'
    return context

class AccommodationListView(LocationListMasterView):
  def get_queryset(self):
    queryset = super().get_queryset()
    # Filter for accommodations
    queryset = queryset.filter(is_accommodation=True)
    return queryset
  
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'accommodations'
    return context

class ActivityListView(LocationListMasterView):
  def get_queryset(self):
    queryset = super().get_queryset()
    # Filter for activities
    queryset = queryset.filter(is_activity=True)
    return queryset
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'activities'
    return context

class AllLocationMapView(LoginRequiredMixin, LocationListMasterView):
  template_name = 'locations/locations_map.html'
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'all'
    return context

class AccommodationMapView(LoginRequiredMixin, LocationListMasterView):
  template_name = 'locations/locations_map.html'
  def get_queryset(self):
    return super().get_queryset().filter(is_accommodation=True)
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'accommodations'
    return context

class ActivityMapView(LoginRequiredMixin, LocationListMasterView):
  template_name = 'locations/locations_map.html'
  def get_queryset(self):
    return super().get_queryset().filter(is_activity=True)
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'activities'
    return context