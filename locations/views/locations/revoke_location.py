from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views import View

from locations.models.Location import Location


class RevokeLocationView(LoginRequiredMixin, PermissionRequiredMixin, View):
  """Staff-only view for toggling a location between published and revoked.

  GET  — returns the revoke/republish form as HTML (for cmnsd modal).
  POST — toggles status: published → revoked, or revoked → published.
         When revoking, optionally saves the reason as a private comment.
  """
  permission_required = 'locations.delete_location'

  template_name = 'locations/revoke_location_form.html'

  def get(self, request, slug):
    location = get_object_or_404(Location, slug=slug)
    context = {'location': location, 'request': request, 'user': request.user}
    html = render_to_string(self.template_name, context, request)
    return JsonResponse({'payload': {'content': html}})

  def post(self, request, slug):
    location = get_object_or_404(Location, slug=slug)

    if location.status == 'p':
      self._revoke(request, location)
    else:
      self._republish(request, location)

    return redirect(location.get_absolute_url())

  def _revoke(self, request, location):
    from locations.models.Comment import Comment
    from django.contrib.contenttypes.models import ContentType

    reason = request.POST.get('reason', '').strip()
    if reason:
      ct = ContentType.objects.get_for_model(location)
      Comment.objects.create(
        content_type=ct,
        object_id=location.pk,
        text=reason,
        title=capfirst(_('revoke reason')),
        visibility='c',
        user=request.user,
        status='p',
      )

    location.status = 'r'
    location.save(update_fields=['status'])
    messages.success(request, capfirst(_('location revoked.')))

  def _republish(self, request, location):
    location.status = 'p'
    location.save(update_fields=['status'])
    messages.success(request, capfirst(_('location republished.')))
