from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views import View

from locations.models import Tag


class DeleteTagView(LoginRequiredMixin, UserPassesTestMixin, View):
  """Staff-only POST view — soft-deletes a tag (status → 'x') if unassigned."""

  def test_func(self):
    return self.request.user.is_staff

  def post(self, request, slug):
    tag = get_object_or_404(Tag.objects.select_related('parent'), slug=slug)
    if tag.locations.filter(status='p').exists():
      messages.error(request, capfirst(_('cannot delete a tag that is still assigned to locations.')))
      return redirect('locations:staff_dashboard')
    tag.status = 'x'
    tag.save(update_fields=['status'])
    label = f'{tag.parent.name}: {tag.name}' if tag.parent else tag.name
    messages.success(request, capfirst(_('tag deleted')) + f': {label}')
    return redirect('locations:staff_dashboard')
