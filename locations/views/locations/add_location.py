from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.utils.text import capfirst

from locations.models.Location import Location
from locations.services.location_geocoding import enrich_location


class AddLocationView(LoginRequiredMixin, CreateView):
  model = Location
  template_name = 'locations/add_location.html'
  fields = ['name', 'address', 'summary']

  def form_valid(self, form):
    from locations.models.Category import Category
    location = form.save(commit=False)
    location.user = self.request.user
    location.save()
    category_slugs = self.request.POST.getlist('categories')
    if category_slugs:
      cats = Category.objects.filter(slug__in=category_slugs, status='p')
      location.categories.set(cats)
    enrich_location(location, request=self.request)
    messages.success(self.request, capfirst(_('location added successfully.')))
    return redirect(location.get_absolute_url())

  def form_invalid(self, form):
    messages.error(self.request, capfirst(_('please correct the errors below.')))
    return super().form_invalid(form)
