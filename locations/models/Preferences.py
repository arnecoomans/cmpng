from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst as capfirst
from django.core.validators import MaxValueValidator, MinValueValidator
from cmnsd.models import BaseModel
from cmnsd.models.BaseMethods import ajax_function, searchable_function, ajax_login_required


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
  

class Visits(BaseModel):
    """Model to track which locations a user has visited."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='visits'
    )
    location = models.ForeignKey('locations.Location', on_delete=models.CASCADE, related_name='visited_by')
    MONTHS = (
        (1, capfirst(_('january'))),
        (2, capfirst(_('february'))),
        (3, capfirst(_('march'))),
        (4, capfirst(_('april'))),
        (5, capfirst(_('may'))),
        (6, capfirst(_('june'))),
        (7, capfirst(_('july'))),
        (8, capfirst(_('august'))),
        (9, capfirst(_('september'))),
        (10, capfirst(_('october'))),
        (11, capfirst(_('november'))),
        (12, capfirst(_('december'))),
    )
    year = models.PositiveIntegerField(help_text=_('year of visit'))
    month = models.PositiveIntegerField(null=True, blank=True, choices=MONTHS)
    day = models.PositiveIntegerField(null=True, blank=True, help_text=_('day of visit'), validators=[MinValueValidator(1), MaxValueValidator(31)])

    class Meta:
      verbose_name_plural = 'Visits'
      ordering = ['location', 'year', 'month', 'day']
    
    def __str__(self):
      return f"{self.user.username} visited {self.location.name} in {self.year}"
    
    @classmethod
    def get_months(cls):
      """Return list of month choices with an additional 'unknown' option."""
      return list(cls.MONTHS)