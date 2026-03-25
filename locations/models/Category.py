from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.conf import settings
from django.utils.text import slugify, capfirst
from django.utils.translation import gettext_lazy as _

from cmnsd.models import BaseModel, VisibilityModel

''' Category model
'''
class Category(BaseModel):
  slug                = models.CharField(max_length=255, unique=True, help_text=f"{ capfirst(_('identifier in URL')) } ({ _('automatically generated') })")
  name                = models.CharField(max_length=255, unique=True, help_text= capfirst(_('Name of category')))
  parent              = models.ForeignKey("self", on_delete=models.CASCADE, related_name='children', null=True, blank=True)

  class Meta:
    verbose_name_plural = 'categories'
    ordering            = [F('parent__name').asc(nulls_first=True), 'name']
    
  def __str__(self) -> str:
    if self.parent:
      return f"{ str(self.parent.name) }: { self.name }"
    return self.name
  
  def save(self, *args, **kwargs):
    # Auto-generate slug from name if not provided
    if not self.slug:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)

  def get_absolute_url(self):
    return reverse_lazy('locations:all') + f"?category={self.slug}"