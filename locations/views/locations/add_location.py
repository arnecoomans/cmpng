from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.utils.text import capfirst

from locations.models.Location import Location
from locations.models.Link import Link
from locations.services.location_geocoding import enrich_location
from locations.services.location_nearby import warn_nearby_duplicates

from urllib import parse

class AddLocationView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
  permission_required = 'locations.add_location'
  model = Location
  template_name = 'locations/add_location.html'
  fields = ['name', 'address', 'summary', 'visibility']

  def form_valid(self, form):
    from locations.models.Category import Category
    location = form.save(commit=False)
    location.user = self.request.user
    location.save()
    category_slugs = self.request.POST.getlist('categories')
    if category_slugs:
      cats = Category.objects.filter(slug__in=category_slugs, status='p')
      location.categories.set(cats)
    link_url = self.request.POST.get('link_url', '').strip()
    if not link_url:
      link_url = 'https://google.com/search?q=' + parse.quote_plus(location.name)
    Link.objects.get_or_create(url=link_url, defaults={'location': location, 'user': self.request.user})
    
    enrich_location(location, request=self.request)
    warn_nearby_duplicates(location, self.request)
    messages.success(self.request, capfirst(_('location added successfully.')))
    return redirect(location.get_absolute_url())

  def form_invalid(self, form):
    messages.error(self.request, capfirst(_('please correct the errors below.')))
    return super().form_invalid(form)
