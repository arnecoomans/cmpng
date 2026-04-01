from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView

from locations.models import Tag


class EditTagView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
  model = Tag
  permission_required = 'locations.change_tag'
  template_name = 'tags/edit_tag.html'
  fields = ['name', 'slug', 'description', 'status']
  success_url = reverse_lazy('locations:tags')
