from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver


def _recalculate(location):
  """Recalculate completeness for a Location instance."""
  if location and location.pk:
    location.calculate_completeness()


# ------------------------------------------------------------------ #
#  Location field changes
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.Location')
def location_saved(sender, instance, **kwargs):
  # Avoid recursion — calculate_completeness uses update_fields internally
  if kwargs.get('update_fields') and 'completeness' in (kwargs['update_fields'] or []):
    return
  _recalculate(instance)


# ------------------------------------------------------------------ #
#  M2M: categories (no through model)
# ------------------------------------------------------------------ #

@receiver(m2m_changed, sender='locations.Location_categories')
def location_categories_changed(sender, instance, **kwargs):
  if kwargs['action'] in ('post_add', 'post_remove', 'post_clear'):
    from locations.models import Location
    if isinstance(instance, Location):
      _recalculate(instance)


# ------------------------------------------------------------------ #
#  Through model: Visits (Location.visitors)
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.Visits')
def visit_saved(sender, instance, **kwargs):
  _recalculate(instance.location)


@receiver(post_delete, sender='locations.Visits')
def visit_deleted(sender, instance, **kwargs):
  _recalculate(instance.location)


# ------------------------------------------------------------------ #
#  Through model: ListItem (Location.list_items)
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.ListItem')
def listitem_saved(sender, instance, **kwargs):
  _recalculate(instance.location)


@receiver(post_delete, sender='locations.ListItem')
def listitem_deleted(sender, instance, **kwargs):
  _recalculate(instance.location)
