from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.conf import settings
from django.utils.text import slugify, capfirst
from django.utils.translation import gettext_lazy as _

from cmnsd.models import BaseModel, VisibilityModel, TranslationAliasMixin

''' Category model
'''
class Category(TranslationAliasMixin, BaseModel):
  slug                = models.CharField(max_length=255, unique=True, help_text=f"{ capfirst(_('identifier in URL')) } ({ _('automatically generated') })")
  name                = models.CharField(max_length=255, unique=True, help_text= capfirst(_('Name of category')))
  aliases             = models.TextField(blank=True, default='', help_text=capfirst(_('comma-separated translations, auto-populated on save')))
  parent              = models.ForeignKey("self", on_delete=models.CASCADE, related_name='children', null=True, blank=True)

  class Meta:
    verbose_name_plural = 'categories'
    ordering            = [F('parent__name').asc(nulls_first=True), 'name']
    
  def __str__(self) -> str:
    if self.parent:
      return f"{ str(self.parent.name) }: { self.name }"
    return self.name
  
  def save(self, *args, **kwargs):
    if not self.slug:
      self.slug = slugify(self.name)
    if 'update_fields' not in kwargs or 'aliases' in (kwargs.get('update_fields') or []):
      self._update_aliases()
    super().save(*args, **kwargs)

  def get_absolute_url(self):
    return reverse_lazy('locations:all') + f"?category={self.slug}"