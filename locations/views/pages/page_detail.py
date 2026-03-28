from django.conf import settings
from django.http import Http404
from django.utils import translation
from django.views.generic import DetailView

from locations.models.Page import Page


class PageDetailView(DetailView):
  model = Page
  template_name = 'pages/page_detail.html'
  context_object_name = 'page'

  def get_object(self, queryset=None):
    slug = self.kwargs['slug']
    active_lang = translation.get_language() or settings.LANGUAGE_CODE
    # Normalise to short code ('en' not 'en-us')
    short_lang = active_lang.split('-')[0]
    default_lang = settings.LANGUAGE_CODE.split('-')[0]

    qs = Page.objects.filter(slug=slug)
    if not self.request.user.is_staff:
      qs = qs.filter(status='p')

    page = qs.filter(language=short_lang).first() or qs.filter(language=default_lang).first()
    if page is None:
      raise Http404
    return page
