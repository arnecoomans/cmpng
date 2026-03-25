from django.views.generic import ListView
from cmnsd.mixins import RequestMixin, FilterMixin

from locations.models.List import List


class ListListView(RequestMixin, FilterMixin, ListView):
  model = List
  template_name = 'lists/lists_list.html'
  context_object_name = 'lists'

  def get_queryset(self):
    if not hasattr(self, '_queryset'):
      queryset = List.objects.prefetch_related('items')
      self._queryset = self.filter(queryset, request=self.request)
    return self._queryset

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'lists'
    return context
