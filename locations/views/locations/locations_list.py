from django.views.generic.list import ListView
from django.contrib import messages
from django.utils.translation import gettext as _
from django.conf import settings
from cmnsd.mixins import RequestMixin, FilterMixin

from math import floor, ceil

from locations.models.Location import Location, Region, Category, Tag

class LocationListMasterView(RequestMixin, FilterMixin, ListView):
  model = Location
  template_name = 'locations/locations_list.html'
  context_object_name = 'locations'
  # paginate_by = settings.ITEMS_PER_PAGE

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
    # Default, show only published locations, but allow filtering for unpublished if user is authenticated and has permission
    request_status = self.request.GET.get('all_status', False)
    if not request_status:
      # Model manager filters visibility based on staff status and user permissions
      # Add filter to show retracted or draft locations after explicitly requesting all status
      queryset = queryset.filter(status='p')

    queryset = queryset.with_visit_state(self.request.user)

    return queryset
  
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # Add preferences to context for template access
    # Get active and applied filters from FilterMixin and add to context for template
    if hasattr(self, 'get_search_data_for_context'):
      context['active_filters'] = self.get_search_data_for_context()
    # Filter options
    context['region_filter_options'] = self.get_region_filter_options(self.get_queryset())
    context['category_filter_options'] = self.get_category_filter_options(self.get_queryset())
    context['tag_filter_options'] = self.get_tag_filter_options(self.get_queryset())
    context['categories'] = Category.objects.filter(
        status='p',
        parent=None  # Only root categories
    ).order_by('name')
    
    context['tags'] = Tag.objects.filter(
        status='p',
        children=None  # Exclude root tags
    ).order_by('name')
    return context
  
  def get_region_filter_options(self, qs):
    countries = {}
    regions = {}
    departments = {}
    for location in qs:
      if location.geo:
        departments[location.geo.id] = {
          'id': location.geo.id,
          'slug': location.geo.slug,
          'name': location.geo.name,
          'region_name': location.geo.name if location.geo else '',  # Include region for context
        }
        if location.geo.parent:
          regions[location.geo.parent.id] = {
            'id': location.geo.parent.id,
            'slug': location.geo.parent.slug,
            'name': location.geo.parent.name,
            'country_name': location.geo.parent.name,  # Include country for context
          }
          if location.geo.parent.parent:  # Check if country level exists
            countries[location.geo.parent.parent.id] = {
              'id': location.geo.parent.parent.id,
              'slug': location.geo.parent.parent.slug,
              'name': location.geo.parent.parent.name,
            }  
    if len(countries) > 1:
      countries = sorted(countries.values(), key=lambda x: x['name'])
      return {'key': 'country', 'label': 'country', 'options': countries}
    elif len(regions) > 1:
      regions = sorted(regions.values(), key=lambda x: x['name'])
      return {'key': 'geo__parent__slug', 'label': 'region', 'options': regions}
    elif len(departments) > 1:
      departments = sorted(departments.values(), key=lambda x: x['name'])
      return {'key': 'geo__slug', 'label': 'department', 'options': departments}
    return {}

  def get_category_filter_options(self, qs):
    # Get categories from the queryset with usage count, limit to top 10, and only include categories used at least once
    # To implement show-all functionality, figure out a way to get intent from the request, and then change limit
    categories_qs = Location.get_categories_from_queryset(qs, limit=10, min_usage=1)
    return {'key': 'category', 'label': 'categories', 'options': list(categories_qs)}
    
  def get_tag_filter_options(self, qs):
    # Get tags from the queryset with usage count, limit to top 10, and only include tags used at least once
    # To implement show-all functionality, figure out a way to get intent from the request, and then change limit
    tags_qs = Location.get_tags_from_queryset(qs, limit=10, min_usage=1)
    return {'key': 'tag', 'label': 'tags', 'options': list(tags_qs)}

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