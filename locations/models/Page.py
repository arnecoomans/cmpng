from django.urls import reverse

from cmnsd.models.Page import PageModel


class Page(PageModel):
  """Concrete static content page for the locations project."""

  def get_absolute_url(self):
    return reverse('locations:page_detail', kwargs={'slug': self.slug})
