from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import View

from locations.models import Location


class ManageListsView(LoginRequiredMixin, PermissionRequiredMixin, View):
  permission_required = 'locations.add_list'
  template_name = 'lists/manage_lists.html'

  def _get_location(self, slug):
    return get_object_or_404(Location, slug=slug)

  def _render(self, request, location):
    location.request = request

    context = {
      'location': location,
      'location_lists': location.filtered_lists(),
      'user_lists': location.owned_lists(),
      'request': request,
      'user': request.user,
    }
    html = render_to_string(self.template_name, context, request)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
      return JsonResponse({'payload': {'content': html}})
    from django.http import HttpResponse
    return HttpResponse(html)

  def get(self, request, slug):
    location = self._get_location(slug)
    return self._render(request, location)
