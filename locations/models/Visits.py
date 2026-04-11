from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst
from django.core.validators import MaxValueValidator, MinValueValidator

from cmnsd.models import BaseModel


class Visits(BaseModel):
  """Model to track which locations a user has visited."""
  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='visits'
  )
  location = models.ForeignKey('locations.Location', on_delete=models.CASCADE, related_name='visited_by')

  RECOMMENDATION_RECOMMEND = 1
  RECOMMENDATION_NEUTRAL = 0
  RECOMMENDATION_DO_NOT_RECOMMEND = -1
  RECOMMENDATION_CHOICES = [
    (RECOMMENDATION_RECOMMEND,        capfirst(_('recommend'))),
    (RECOMMENDATION_NEUTRAL,          capfirst(_('neutral'))),
    (RECOMMENDATION_DO_NOT_RECOMMEND, capfirst(_('do not recommend'))),
  ]
  recommendation = models.IntegerField(
    choices=RECOMMENDATION_CHOICES,
    null=True,
    blank=True,
    verbose_name=_('recommendation'),
  )

  MONTHS = (
    (1,  capfirst(_('january'))),
    (2,  capfirst(_('february'))),
    (3,  capfirst(_('march'))),
    (4,  capfirst(_('april'))),
    (5,  capfirst(_('may'))),
    (6,  capfirst(_('june'))),
    (7,  capfirst(_('july'))),
    (8,  capfirst(_('august'))),
    (9,  capfirst(_('september'))),
    (10, capfirst(_('october'))),
    (11, capfirst(_('november'))),
    (12, capfirst(_('december'))),
  )
  year = models.PositiveIntegerField(help_text=_('year of visit'))
  month = models.PositiveIntegerField(null=True, blank=True, choices=MONTHS)
  day = models.PositiveIntegerField(
    null=True, blank=True,
    help_text=_('day of visit'),
    validators=[MinValueValidator(1), MaxValueValidator(31)],
  )

  end_year = models.PositiveIntegerField(null=True, blank=True, help_text=_('year of last day of visit'))
  end_month = models.PositiveIntegerField(null=True, blank=True, choices=MONTHS)
  end_day = models.PositiveIntegerField(
    null=True, blank=True,
    help_text=_('day of last day of visit'),
    validators=[MinValueValidator(1), MaxValueValidator(31)],
  )

  class Meta:
    verbose_name_plural = 'Visits'
    ordering = ['location', 'year', 'month', 'day']

  def __str__(self):
    start = str(self.year)
    if self.end_year and self.end_year != self.year:
      return f"{self.user.username} visited {self.location.name} ({start}–{self.end_year})"
    return f"{self.user.username} visited {self.location.name} ({start})"

  def clean(self):
    from django.core.exceptions import ValidationError
    if self.end_year and self.end_year < self.year:
      raise ValidationError({'end_year': _('End year cannot be before start year.')})
    if (
      self.end_year == self.year
      and self.end_month and self.month
      and self.end_month < self.month
    ):
      raise ValidationError({'end_month': _('End month cannot be before start month in the same year.')})
    if (
      self.end_year == self.year
      and self.end_month == self.month
      and self.end_day and self.day
      and self.end_day < self.day
    ):
      raise ValidationError({'end_day': _('End day cannot be before start day in the same month.')})

  def nights(self):
    """Return the number of nights between start and end date, or None if not calculable."""
    if not self.end_year:
      return None
    from datetime import date
    start = date(self.year, self.month or 1, self.day or 1)
    end = date(self.end_year, self.end_month or 1, self.end_day or 1)
    delta = (end - start).days
    return delta if delta > 0 else None

  @classmethod
  def get_months(cls):
    """Return list of month choices."""
    return list(cls.MONTHS)
