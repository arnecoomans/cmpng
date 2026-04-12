import csv
import io
import zipfile
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from locations.models import Location, List, ListItem
from locations.models.Visits import Visits
from locations.models.Comment import Comment
from locations.models.Media import Media
from locations.models.Preferences import UserPreferences


EXPORT_SECTIONS = [
  ('profile',   capfirst(_('profile & preferences'))),
  ('visits',    capfirst(_('visits'))),
  ('comments',  capfirst(_('comments'))),
  ('locations', capfirst(_('locations added'))),
  ('media',     capfirst(_('media added'))),
  ('lists',     capfirst(_('lists'))),
]

_RECOMMENDATION_LABELS = {
  Visits.RECOMMENDATION_RECOMMEND:       'recommended',
  Visits.RECOMMENDATION_NEUTRAL:         'neutral',
  Visits.RECOMMENDATION_DO_NOT_RECOMMEND: 'not recommended',
}


def _csv_bytes(headers, rows):
  """Return a CSV file as bytes."""
  buf = io.StringIO()
  writer = csv.writer(buf)
  writer.writerow(headers)
  writer.writerows(rows)
  return buf.getvalue().encode('utf-8')


def _build_zip(user, sections):
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

    if 'profile' in sections:
      prefs = UserPreferences.objects.filter(user=user).select_related('home').prefetch_related('family', 'favorites').first()
      rows = [[
        user.get_full_name(),
        user.username,
        user.email,
        prefs.language if prefs else '',
        prefs.home.name if prefs and prefs.home else '',
        ', '.join(u.username for u in prefs.family.all()) if prefs else '',
        ', '.join(loc.name for loc in prefs.favorites.all()) if prefs else '',
      ]]
      zf.writestr('profile.csv', _csv_bytes(
        ['name', 'username', 'email', 'language', 'home', 'family', 'favorites'],
        rows,
      ))

    if 'visits' in sections:
      rows = [
        [
          v.location.name,
          v.year, v.month, v.day,
          v.end_year, v.end_month, v.end_day,
          _RECOMMENDATION_LABELS.get(v.recommendation, '') if v.recommendation is not None else '',
        ]
        for v in Visits.objects.filter(user=user).select_related('location').order_by('year', 'month', 'day')
      ]
      zf.writestr('visits.csv', _csv_bytes(
        ['location', 'year', 'month', 'day', 'end_year', 'end_month', 'end_day', 'recommendation'],
        rows,
      ))

    if 'comments' in sections:
      rows = [
        [
          c.content_object.name if hasattr(c.content_object, 'name') else str(c.content_object),
          c.title, c.text, c.visibility, c.status,
          c.date_created.date().isoformat(),
        ]
        for c in Comment.objects.filter(user=user).order_by('date_created')
      ]
      zf.writestr('comments.csv', _csv_bytes(
        ['location', 'title', 'text', 'visibility', 'status', 'date_created'],
        rows,
      ))

    if 'locations' in sections:
      rows = [
        [
          loc.name, loc.description, loc.address, loc.status, loc.visibility,
          loc.date_created.date().isoformat(),
          loc.date_modified.date().isoformat(),
        ]
        for loc in Location.objects.filter(user=user).order_by('date_created')
      ]
      zf.writestr('locations.csv', _csv_bytes(
        ['name', 'description', 'address', 'status', 'visibility', 'date_created', 'date_modified'],
        rows,
      ))

    if 'media' in sections:
      rows = [
        [
          m.location.name if m.location else '',
          m.title, m.source, m.visibility, m.status,
          m.date_created.date().isoformat(),
        ]
        for m in Media.objects.filter(user=user).select_related('location').order_by('date_created')
      ]
      zf.writestr('media.csv', _csv_bytes(
        ['location', 'title', 'source', 'visibility', 'status', 'date_created'],
        rows,
      ))

    if 'lists' in sections:
      rows = [
        [
          item.list.name,
          item.list.template,
          item.location.name if item.location else '',
          item.order,
          item.stay_duration,
          item.price_per_night,
          item.note,
        ]
        for item in ListItem.objects.filter(
          list__user=user,
        ).select_related('list', 'location').order_by('list__name', 'order')
      ]
      zf.writestr('lists.csv', _csv_bytes(
        ['list', 'template', 'location', 'order', 'stay_duration', 'price_per_night', 'note'],
        rows,
      ))

  buf.seek(0)
  return buf


class ExportDataView(LoginRequiredMixin, TemplateView):
  template_name = 'preferences/export_data.html'

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['sections'] = EXPORT_SECTIONS
    return context

  def post(self, request):
    selected = [key for key, _ in EXPORT_SECTIONS if key in request.POST]
    if not selected:
      selected = [key for key, _ in EXPORT_SECTIONS]

    buf = _build_zip(request.user, selected)
    filename = f'cmpng-export-{request.user.username}-{date.today().isoformat()}.zip'

    response = HttpResponse(buf.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
