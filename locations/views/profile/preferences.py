from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from locations.models.Preferences import UserPreferences, App
from locations.templatetags.maps_tags import SESSION_KEY


class PreferencesView(LoginRequiredMixin, TemplateView):
  template_name = 'preferences/preferences.html'

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
    context['preferences'] = preferences
    context['available_apps'] = App.objects.all()
    return context


class RevokeMapsSessionView(LoginRequiredMixin, View):
  def post(self, request):
    request.session.pop(SESSION_KEY, None)
    return redirect('locations:preferences')
