from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.views import View

from cmnsd.models.BaseModel import BaseModel
from locations.models.Location import Location

_STATUS_LABELS = dict(BaseModel.status_choices)


class CheckDuplicateView(LoginRequiredMixin, View):
  """Return candidate duplicate locations matching a name query.

  Searches across all statuses so revoked and deleted locations surface.
  Scoped to the requesting user's own locations; staff see all.

  GET /locations/location/add/check-duplicate/?q=<name>
  """

  def get(self, request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
      return self._json([])

    qs = Location.objects.filter(name__icontains=q)
    if not request.user.is_staff:
      qs = qs.filter(user=request.user)

    matches = []
    for loc in qs.order_by('status', 'name')[:10]:
      matches.append({
        'name': loc.name,
        'status': loc.status,
        'status_label': str(_STATUS_LABELS.get(loc.status, loc.status)).lower(),
        'slug': loc.slug,
        'url': loc.get_absolute_url() if loc.status == 'p' else None,
        'can_unrevoke': loc.status == 'r' and (
          request.user.is_staff or loc.user_id == request.user.pk
        ),
      })

    return self._json(matches)

  def _json(self, matches):
    return HttpResponse(
      DjangoJSONEncoder().encode({'matches': matches}),
      content_type='application/json',
    )
