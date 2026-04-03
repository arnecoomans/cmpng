import hashlib
import os
from datetime import date
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models

from cmnsd.models import BaseModel, VisibilityModel


def media_upload_path(instance, filename):
  return f"images/locations/{date.today().strftime('%Y-%m-%d')}-{filename}"


class Media(VisibilityModel, BaseModel):
  source = models.ImageField(upload_to=media_upload_path)
  title = models.CharField(max_length=255, blank=True)
  file_hash = models.CharField(max_length=64, blank=True, db_index=True)
  location = models.ForeignKey(
    'locations.Location',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='media'
  )

  class Meta:
    verbose_name_plural = 'media'
    ordering = ['visibility', '-date_modified']

  def __str__(self):
    name = self.location.name if self.location else 'no location'
    return f"{self.title} ({name})"

  def save(self, *args, **kwargs):
    if not self.title:
      self.title = self.source.name.replace('_', ' ')
    self._convert_heic_to_jpg()
    if self.source and not self.file_hash:
      self.source.seek(0)
      self.file_hash = hashlib.sha256(self.source.read()).hexdigest()
      self.source.seek(0)
    super().save(*args, **kwargs)

  def _convert_heic_to_jpg(self):
    """Convert HEIC/HEIF uploads to JPEG in-place before saving."""
    if not self.source:
      return
    name = self.source.name or ''
    if not name.lower().endswith(('.heic', '.heif')):
      return

    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()

    image = Image.open(self.source)
    image = image.convert('RGB')

    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=90)
    buffer.seek(0)

    new_name = os.path.splitext(os.path.basename(name))[0] + '.jpg'
    self.source.save(new_name, ContentFile(buffer.read()), save=False)
