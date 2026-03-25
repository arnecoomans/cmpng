from django.db import models
from cmnsd.models.Comment import BaseComment

class Comment(BaseComment):
  # Declare allowed parent models for AJAX dispatch creation.
  # Client sends content_for=location + content_token=<token>.
  # Dispatch resolves ContentType server-side — no raw IDs cross the wire.
  content_type_map = {
    'location': 'locations.location',
  }

  class Meta:
    verbose_name = 'comment'
    verbose_name_plural = 'comments'
    ordering = ['-date_created']
    indexes = [
      models.Index(fields=['content_type', 'object_id'], name='comment_ct_object_idx'),
      models.Index(fields=['status'], name='comment_status_idx'),
    ]
