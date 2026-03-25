from django.views.generic import ListView
from cmnsd.mixins import RequestMixin, FilterMixin

from locations.models import Comment


class CommentListView(RequestMixin, FilterMixin, ListView):
  model = Comment
  template_name = 'comments/comments_list.html'
  context_object_name = 'comments'
  paginate_by = 20

  def get_queryset(self):
    if not hasattr(self, '_optimized_queryset'):
      queryset = Comment.objects.select_related(
        'user', 'content_type'
      ).order_by('-date_created')
      self._optimized_queryset = self.filter(queryset, request=self.request)
    return self._optimized_queryset

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'comments'
    if hasattr(self, 'get_search_data_for_context'):
      context['active_filters'] = self.get_search_data_for_context()
    return context
