# locations/models/Size.py
from django.db import models
from cmnsd.models import BaseModel

class Size(BaseModel):
  """Size classification for locations."""
  
  code = models.CharField(max_length=10, db_index=True)
  name = models.CharField(max_length=50)
  description = models.TextField(blank=True)
  order = models.IntegerField(default=0)
  categories = models.ManyToManyField('Category', related_name='sizes')
  
  class Meta:
      ordering = ['order', 'name']
  
  def __str__(self):
    cats = ', '.join(self.categories.values_list('name', flat=True))
    return f"{self.name} ({cats})" if cats else self.name