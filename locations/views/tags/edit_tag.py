from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView

from locations.models import Tag


class EditTagView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
  model = Tag
  permission_required = 'locations.change_tag'
  template_name = 'tags/edit_tag.html'
  fields = ['name', 'slug', 'description', 'parent', 'status', 'similarity_weight']
  success_url = reverse_lazy('locations:tags')

  def get_form(self, form_class=None):
    form = super().get_form(form_class)
    form.fields['parent'].required = False
    if self.request.method == 'POST':
      parent_id = self.request.POST.get('parent__id')
      if parent_id:
        form.data = form.data.copy()
        form.data['parent'] = parent_id
    return form
