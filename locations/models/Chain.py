from django.db import models
from django.urls import reverse_lazy
from django.utils.text import slugify, capfirst
from django.utils.translation import gettext_lazy as _

from cmnsd.models import BaseModel

''' Location Chain model
    When a location is part of a chain (mother company), it can be useful to locate other locations by the 
    same chain. Since often services and level of quality are alike. 
'''
class Chain(BaseModel):
  ''' Internal Identifier '''
  slug                = models.CharField(max_length=255, unique=True, help_text=f"{ capfirst(_('identifier in URL')) } ({ _('automatically generated') })")

  ''' Location information '''
  name                = models.CharField(max_length=255, unique=True, help_text=capfirst(_('name of location as it is identified by')))
  parent              = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')

  def __str__(self):
    if self.parent:
      return f"{ self.name } ({ str(self.parent) })"
    return self.name
  
  def save(self, *args, **kwargs):
    # Generate slug from name if not provided
    if not self.slug:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)