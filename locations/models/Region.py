from django.db import models
from django.urls import reverse_lazy
from django.utils.text import slugify, capfirst
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from cmnsd.models import BaseModel, VisibilityModel

class Region(BaseModel, VisibilityModel):
  slug                = models.CharField(max_length=255, unique=True, help_text=f"{ capfirst(_('identifier in URL')) } ({ _('automatically generated') })")
  
  name                = models.CharField(max_length=255)
  parent              = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
  
  LEVEL_CHOICES = (
    ('country', capfirst(_('country'))),
    ('region', capfirst(_('region'))),
    ('department', capfirst(_('department'))),
    ('locality', capfirst(_('locality'))),
  )
  level = models.CharField(
    max_length=10,
    choices=LEVEL_CHOICES,
    editable=False,
    help_text=f"{ capfirst(_('the level of the region based on its position in the hierarchy')) } ({ _('automatically calculated') })"
  )
  # Cached average distance
  cached_average_distance_to_center = models.FloatField(
    null=True,
    blank=True,
    help_text=capfirst(_('average distance of all locations/subregions in this region'))
  )

  class Meta:
    ordering = ['parent__parent__name', 'parent__name', 'name']
    unique_together = ('parent', 'slug')  # Ensure unique slug within the same parent region
  
  def __str__(self) -> str:
    if self.parent:
      return ', '.join([str(self.name), str(self.parent)])
    return self.name
  
  def save(self, *args, **kwargs):
    # Ensure slug is generated from name if not provided
    if not self.slug:
      self.slug = slugify(self.name)
    # Ensure level is calculated based on parent-child relationships
    self.level = self._calculate_level()
    # Validate fields before saving
    self.full_clean()
    # Call the original save method
    super().save(*args, **kwargs)

  # Save Functions
  ''' Calculate Level:
      Calculate the level of the region based on its position in the hierarchy
      Level is determined by the number of parent regions:
      - 0 parents: country
      - 1 parent: region
      - 2 parents: department
      - 3 or more parents: locality
  '''
  def _calculate_level(self):
    depth = 0
    node = self
    while node.parent_id:
        depth += 1
        node = node.parent
    return {
        0: 'country',
        1: 'region',
        2: 'department',
    }.get(depth, 'locality')
  
  def clean(self):
    """
      Validate name uniqueness within the same parent scope.

      Ensures no two records of the same model share the same name
      under the same parent. If the model has no 'name' field, the
      check is skipped. If the model has no 'parent' field, uniqueness
      is checked globally across all records of that model.

      This method is called automatically when full_clean() is invoked,
      which happens on every save() in models that call full_clean()
      before super().save().

      Raises:
          ValidationError: If a record with the same name (and parent,
              if applicable) already exists.

      Examples:
          # Region has both name and parent — uniqueness is scoped:
          # 'Utrecht' under 'Netherlands' and 'Utrecht' under 'Utrecht
          # region' are both valid, but two 'Utrecht' entries under
          # 'Netherlands' are not.

          # A model with only name and no parent — uniqueness is global:
          # two records named 'Foobar' cannot coexist.
    """
    qs = Region.objects.filter(
      name=self.name,
      parent=self.parent,
    )
    if self.pk:
      qs = qs.exclude(pk=self.pk)
    if qs.exists():
      raise ValidationError({
        'name': capfirst(_('a region with this name already exists under the same parent.')),
        'record': self.__str__(),
      })

  def calculate_average_distance_to_center(self):
    """
    Calculate average distance to departure center for this region.
    Considers both direct child locations and child regions.
    Recursively updates parent regions.
    """
    distances = []
    
    # Get distances from direct locations
    location_distances = self.locations.filter(
      distance_to_departure_center__isnull=False
    ).values_list('distance_to_departure_center', flat=True)
    distances.extend(location_distances)
    
    # Get distances from child regions
    child_distances = self.children.filter(
      cached_average_distance_to_center__isnull=False
    ).values_list('cached_average_distance_to_center', flat=True)
    distances.extend(child_distances)
    
    # Calculate average if we have data
    if distances:
      self.cached_average_distance_to_center = sum(distances) / len(distances)
      self.save(update_fields=['cached_average_distance_to_center'])
    else:
      self.cached_average_distance_to_center = None
      self.save(update_fields=['cached_average_distance_to_center'])
    
    # Recursively update parent
    if self.parent:
      self.parent.calculate_average_distance_to_center()
    
    return self.cached_average_distance_to_center
  
  # Region Type Functions
  def get_region_by_type(self, type):
    # Walk up the hierarchy to find the region of the specified type
    """Helper to get region of a specific type in the hierarchy."""
    if self.level == type:
      return self
    elif self.parent:
      return self.parent.get_region_by_type(type)
    else:
      return None
  @property
  def country(self):
    return self.get_region_by_type('country')
  @property
  def region(self):
    return self.get_region_by_type('region')
  @property
  def department(self):
    return self.get_region_by_type('department')
  @property
  def locality(self):
    return self.get_region_by_type('locality')