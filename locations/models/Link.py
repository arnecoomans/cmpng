from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse

from cmnsd.models.Link import BaseLink


class Link(BaseLink):
  location = models.ForeignKey(
    'Location',
    on_delete=models.CASCADE,
    related_name='links'
  )