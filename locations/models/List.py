from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from django.utils.text import slugify

from cmnsd.models import BaseModel, VisibilityModel


# ================================================================
# Distance
# Cached Google API result for a pair of locations.
# Always stored with the lower-pk location as origin to avoid
# duplicate entries for A→B and B→A.
# ================================================================
class Distance(models.Model):
  origin       = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='distances_as_origin')
  destination  = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='distances_as_destination')
  distance_m   = models.FloatField()
  duration_s  = models.FloatField()
  cached_at    = models.DateTimeField(default=now)

  class Meta:
    unique_together = ('origin', 'destination')

  def __str__(self):
    return f"{self.origin} → {self.destination} ({self.distance_m / 1000:.2f} km, {self.duration_s / 60:.2f} min)"

  # ================================================================
  # Normalize pair so origin.pk is always the smaller of the two.
  # ================================================================
  @staticmethod
  def normalize(a, b):
    """Return (origin, destination) with the lower-pk location first."""
    return (a, b) if a.pk < b.pk else (b, a)

  # ================================================================
  # Retrieve a cached Distance or return None (no API call here —
  # API calls belong in a service layer).
  # ================================================================
  @classmethod
  def get_for(cls, a, b):
    """Return the cached Distance for locations a and b, or None."""
    origin, destination = cls.normalize(a, b)
    return cls.objects.filter(origin=origin, destination=destination).first()
  # ================================================================
  # Human readable distance and duration properties.
  # ================================================================
  def distance_km(self):
    return self.distance_m / 1000
  def duration_min(self):
    return self.duration_s / 60
  def duration_hr(self):
    return self.duration_s / 3600

# ================================================================
# List
# A named, ordered collection of locations forming a trip plan.
# ================================================================
class List(BaseModel, VisibilityModel):

  TEMPLATE_ITINERARY  = 'itinerary'
  TEMPLATE_BUCKETLIST = 'bucketlist'
  TEMPLATE_THEMED     = 'themed'
  TEMPLATE_LOGBOOK    = 'logbook'
  TEMPLATE_CHOICES = [
    (TEMPLATE_ITINERARY,  _('Itinerary')),   # sequential trip with legs, dates, distances
    (TEMPLATE_BUCKETLIST, _('Bucket list')), # unordered wishlist, no routing
    (TEMPLATE_THEMED,     _('Themed list')), # e.g. "top 10 family campings", story-style
    (TEMPLATE_LOGBOOK,    _('Logbook')),     # visited places, chronological record
  ]

  locations   = models.ManyToManyField(
    'Location',
    through='ListItem',
    related_name='lists',
  )
  name        = models.CharField(max_length=200)
  slug        = models.SlugField(max_length=200, unique=True, blank=True)
  description = models.TextField(blank=True, default='')
  template    = models.CharField(
    max_length=20,
    choices=TEMPLATE_CHOICES,
    default=TEMPLATE_ITINERARY,
  )
  is_archived = models.BooleanField(
    default=False,
    help_text=_('Archived lists are read-only and hidden from active views.'),
  )

  class Meta:
    ordering = ['-date_created']

  def __str__(self):
    return self.name

  def save(self, *args, **kwargs):
    if not self.slug and self.name:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)

  @property
  def is_routed(self):
    """True for templates where leg distances and ordering are meaningful."""
    return self.template == self.TEMPLATE_ITINERARY

  @classmethod
  def get_optimized_queryset(cls):
    return cls.objects.prefetch_related(
      models.Prefetch(
        'items',
        queryset=ListItem.objects.select_related(
          'location',
          'media',
          'leg_distance__origin',
          'leg_distance__destination',
        ).order_by('order'),
      )
    )


# ================================================================
# ListItem
# A single stop in a List, with ordering, optional stay details,
# and a cached leg distance from the previous stop (or home).
# ================================================================
class ListItem(models.Model):
  list            = models.ForeignKey(List, on_delete=models.CASCADE, related_name='items')
  location        = models.ForeignKey('Location', on_delete=models.CASCADE, related_name='list_items')
  order           = models.PositiveIntegerField(default=0)
  note            = models.TextField(blank=True, default='')

  # Accommodation-specific (optional)
  stay_duration   = models.PositiveSmallIntegerField(null=True, blank=True, help_text=_('Number of nights'))
  price_per_night = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

  # Optional featured media from this location's media library
  media           = models.ForeignKey('Media', on_delete=models.SET_NULL, null=True, blank=True, related_name='list_items')

  # Cached leg: distance from the previous item (or home) to this location
  leg_distance    = models.ForeignKey(Distance, on_delete=models.SET_NULL, null=True, blank=True, related_name='list_items')

  class Meta:
    ordering = ['order']
    unique_together = ('list', 'order')

  def __str__(self):
    try:
      return f"{self.list} #{self.order}: {self.location.name}"
    except:
      return f"LIST #{self.order}: LOCATION"
    
