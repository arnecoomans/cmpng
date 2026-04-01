from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views.generic import ListView
from cmnsd.mixins import RequestMixin, FilterMixin
from locations.models import Visits, Location

class ManageVisitsView(LoginRequiredMixin, PermissionRequiredMixin, RequestMixin, FilterMixin, ListView):
  permission_required = 'locations.add_visits'
  model = Visits
  template_name = 'visits/manage_visits.html'
  context_object_name = 'visits'

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['scope'] = 'visits'
    context['months'] = self.model.get_months()
    context['location'] = Location.objects.filter(slug=self.kwargs.get('slug')).first() if 'slug' in self.kwargs else None
    return context

  def get_queryset(self):
    queryset = self.model.objects.filter(user=self.request.user)
    if 'slug' in self.kwargs:
      queryset = queryset.filter(location__slug=self.kwargs['slug'])
    queryset = self.filter_status(queryset, request=self.request)
    queryset = self.filter_visibility(queryset, request=self.request)
    return queryset

  def get(self, request, *args, **kwargs):
    self.object_list = self.get_queryset()
    context = self.get_context_data()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
      html = render_to_string(self.template_name, context, request)
      return JsonResponse({'payload': {'content': html}})

    return self.render_to_response(context)
