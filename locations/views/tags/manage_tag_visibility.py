import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from locations.models import Tag


class ManageTagVisibilityView(LoginRequiredMixin, PermissionRequiredMixin, View):
  permission_required = 'locations.change_tag'
  template_name = 'tags/manage_tag_visibility.html'

  def get(self, request):
    tags = Tag.objects.filter(children__isnull=True).select_related('parent').order_by('parent__name', 'name')
    columns = {key: [] for key, _ in Tag.visibility_choices}
    for tag in tags:
      columns[tag.visibility].append(tag)

    return render(request, self.template_name, {
      'columns': columns,
      'visibility_labels': dict(Tag.visibility_choices),
    })

  def post(self, request):
    try:
      data = json.loads(request.body)
      tag_id    = data.get('tag_id')
      visibility = data.get('visibility')
    except (ValueError, KeyError):
      return JsonResponse({'error': 'invalid request'}, status=400)

    valid = {v for v, _ in Tag.visibility_choices}
    if visibility not in valid:
      return JsonResponse({'error': 'invalid visibility'}, status=400)

    updated = Tag.objects.filter(pk=tag_id).update(visibility=visibility)
    if not updated:
      return JsonResponse({'error': 'tag not found'}, status=404)

    return JsonResponse({'ok': True})
