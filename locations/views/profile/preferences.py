from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.translation import activate
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


class SetLanguageView(LoginRequiredMixin, View):
  def post(self, request):
    lang = request.POST.get('language')
    valid_langs = [code for code, _ in settings.LANGUAGES]
    if lang in valid_langs:
      preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
      preferences.language = lang
      preferences.save(update_fields=['language'])
      activate(lang)
      response = redirect('locations:preferences')
      response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
      )
      return response
    return redirect('locations:preferences')


class RevokeMapsSessionView(LoginRequiredMixin, View):
  def post(self, request):
    request.session.pop(SESSION_KEY, None)
    return redirect('locations:preferences')
