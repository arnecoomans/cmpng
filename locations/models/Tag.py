from django.db import models
from django.utils.translation import gettext_lazy as _

from django.urls import reverse_lazy

from cmnsd.models import VisibilityModel
from cmnsd.models.TagModel import TagModel

class Tag(VisibilityModel, TagModel):
  class Meta:
    ordering = ['parent__name', 'name']

  @classmethod
  def get_optimized_queryset(cls):
    return cls.objects.select_related('parent').order_by('parent__name', 'name')

  @classmethod
  def get_searchable_fields(cls):
    return ['name', 'slug', 'description']

  @classmethod
  def get_filter_mapping(cls):
    return {
      'parent': 'parent__slug',
    }

  def get_absolute_url(self):
    return reverse_lazy('locations:all') + f'?tag={self.slug}'
  
  def accommodations(self):
    return self.locations.filter(is_accommodation=True)
  def activities(self):
    return self.locations.filter(is_activity=True)
    