from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import View

from locations.models import Location
from locations.models.Media import Media


class ManageMediaView(LoginRequiredMixin, PermissionRequiredMixin, View):
  permission_required = 'locations.change_media'
  template_name = 'media/manage_media.html'

  def _get_location(self, slug):
    return get_object_or_404(Location, slug=slug)

  def _render(self, request, location):
    location.request = request
    media = location.ordered_media
    context = {
      'location': location,
      'media': media,
      'request': request,
      'user': request.user,
    }
    html = render_to_string(self.template_name, context, request)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
      return JsonResponse({'payload': {'content': html}})
    return HttpResponse(html)

  def get(self, request, slug):
    location = self._get_location(slug)
    return self._render(request, location)

  def post(self, request, slug):
    location = self._get_location(slug)
    file = request.FILES.get('source')
    valid_visibilities = {c[0] for c in Media.visibility_choices}
    visibility = request.POST.get('visibility', '')
    if visibility not in valid_visibilities:
      visibility = 'c'
    if file:
      Media.objects.create(
        location=location,
        source=file,
        title=request.POST.get('title', ''),
        visibility=visibility,
        user=request.user,
      )
    return self._render(request, location)
