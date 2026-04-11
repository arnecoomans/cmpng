from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst as capfirst
from cmnsd.models.BaseMethods import ajax_function, ajax_login_required


class App(models.Model):
  """External apps that can be linked from a location (e.g. Google Maps, Waze)."""
  slug = models.SlugField(unique=True)
  label = models.CharField(max_length=100)
  url_format = models.CharField(
    max_length=500,
    help_text=_('URL template with placeholders, e.g. https://waze.com/ul?ll={lat},{lon}'))
  CATEGORY_CHOICES = [
    ('navigation', capfirst(_('navigation'))),
    ]
  category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True)
  default_enabled = models.BooleanField(default=True)

  class Meta:
    ordering = ['label']

  def __str__(self):
    return self.label

class UserPreferences(models.Model):
    """Persistent preferences for authenticated users."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Preference fields
    language = models.CharField(max_length=10, choices=settings.LANGUAGES, null=True, blank=True)
    home = models.ForeignKey('locations.Location', null=True, blank=True, on_delete=models.SET_NULL, related_name='home_of')
    family = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, help_text=_('family members'), related_name='family_of')
    external_maps_consent = models.BooleanField(default=False)
    favorites = models.ManyToManyField('locations.Location', related_name='favorited', blank=True)
    hidden_locations = models.ManyToManyField('locations.Location', related_name='hidden_by', blank=True)
    apps = models.ManyToManyField(App, related_name='users_with_app', blank=True)
    date_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'User preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    RESTRICT_READ_ACCESS = 'user'  # only allow users to read their own visits via AJAX

    @ajax_function
    def all_apps(self):
      apps = App.objects.all()
      list = []
      for app in apps:
        list.append({
          'id': app.id,
          'slug': app.slug,
          'label': app.label,
          'url_format': app.url_format,
          'category': app.category,
          'default_enabled': app.default_enabled,
          'enabled': self.apps.filter(pk=app.pk).exists(),
        })
      return list

    @ajax_login_required
    def available_family(self):
      """Return list of users that can be added as family members (i.e. not already added)."""
      from django.contrib.auth import get_user_model
      return get_user_model().objects.exclude(pk__in=self.family.all()).exclude(pk=self.user.pk).values('id', 'username', 'first_name', 'last_name')