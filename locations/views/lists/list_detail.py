from django.views.generic import DetailView
from django.core.exceptions import PermissionDenied
from cmnsd.mixins import RequestMixin, FilterMixin

from locations.models.List import List, ListItem


class ListDetailView(RequestMixin, FilterMixin, DetailView):
  model = List
  template_name = 'lists/list_detail.html'
  context_object_name = 'list'
  slug_field = 'slug'
  slug_url_kwarg = 'slug'

  def get_object(self, queryset=None):
    obj = super().get_object(queryset)
    if not obj.is_visible_to(self.request.user):
      raise PermissionDenied
    return obj

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['items'] = (
      self.object.items
        .select_related('location__geo__parent__parent', 'leg_distance')
        .order_by('order')
    )
    context['scope'] = 'list_detail'
    return context
