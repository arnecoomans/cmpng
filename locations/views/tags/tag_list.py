from django.views.generic import ListView
from cmnsd.mixins import RequestMixin, FilterMixin

from locations.models import Tag


class TagListView(RequestMixin, FilterMixin, ListView):
  model = Tag
  template_name = 'tags/tags_list.html'
  context_object_name = 'tags'

  def get_queryset(self):
    if not hasattr(self, '_optimized_queryset'):
      queryset = Tag.get_optimized_queryset()
      mapping = Tag.get_filter_mapping()
      self._optimized_queryset = self.filter(queryset, mapping=mapping, request=self.request)
      if not self.request.user.is_staff:
        self._optimized_queryset = self._optimized_queryset.filter(children__isnull=True).distinct()
    return self._optimized_queryset

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'tags'
    if hasattr(self, 'get_search_data_for_context'):
      context['active_filters'] = self.get_search_data_for_context()
    return context
