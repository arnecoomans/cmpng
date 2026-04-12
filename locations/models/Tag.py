from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from django.urls import reverse_lazy

from cmnsd.models import VisibilityModel, TranslationAliasMixin
from cmnsd.models.TagModel import TagModel

class Tag(TranslationAliasMixin, VisibilityModel, TagModel):
  visibility = models.CharField(
      max_length=1,
      choices=VisibilityModel.visibility_choices,
      default='c',
  )
  similarity_weight = models.PositiveSmallIntegerField(
      default=100,
      help_text=capfirst(_('relative weight used in similarity scoring; increase for tags that strongly define a location (default: 100)')),
  )

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

  def save(self, *args, **kwargs):
    if 'update_fields' not in kwargs or 'aliases' in (kwargs.get('update_fields') or []):
      self._update_aliases()
    super().save(*args, **kwargs)

  def get_absolute_url(self):
    return reverse_lazy('locations:all') + f'?tag={self.slug}'
  
  def accommodations(self):
    return self.locations.filter(is_accommodation=True)
  def activities(self):
    return self.locations.filter(is_activity=True)
    