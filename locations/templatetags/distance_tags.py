from django import template

from locations.models.List import Distance

register = template.Library()


@register.simple_tag
def distance_between(location_a, location_b):
  """
  Return the cached Distance between two locations, or None.

  Usage:
    {% distance_between location user.preferences.home as dist %}
    {% if dist %}{{ dist.distance_m }}{% endif %}
  """
  if not location_a or not location_b:
    return None
  if location_a.pk == location_b.pk:
    return None
  return Distance.get_for(location_a, location_b)
