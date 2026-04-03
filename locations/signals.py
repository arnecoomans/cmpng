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
def location_saved(sender, instance, raw, **kwargs):
  if raw:
    return
  # Avoid recursion — calculate_completeness uses update_fields internally
  if kwargs.get('update_fields') and 'completeness' in (kwargs['update_fields'] or []):
    return
  _recalculate(instance)


# ------------------------------------------------------------------ #
#  M2M: categories (no through model)
# ------------------------------------------------------------------ #

@receiver(m2m_changed, sender='locations.Location_categories')
def location_categories_changed(sender, instance, action, pk_set, **kwargs):
  if action in ('post_add', 'post_remove', 'post_clear'):
    from locations.models import Location
    if isinstance(instance, Location):
      _recalculate(instance)
  if action == 'post_add' and pk_set:
    from locations.models import Location, Category
    if isinstance(instance, Location):
      if Category.objects.filter(pk__in=pk_set, slug='home').exists():
        Location.objects.filter(pk=instance.pk).update(visibility='f')
        instance.visibility = 'f'


# ------------------------------------------------------------------ #
#  Through model: Visits (Location.visitors)
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.Visits')
def visit_saved(sender, instance, raw, **kwargs):
  if raw:
    return
  _recalculate(instance.location)


@receiver(post_delete, sender='locations.Visits')
def visit_deleted(sender, instance, **kwargs):
  _recalculate(instance.location)


# ------------------------------------------------------------------ #
#  Media
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.Media')
def media_saved(sender, instance, raw, **kwargs):
  if raw:
    return
  _recalculate(instance.location)


@receiver(post_delete, sender='locations.Media')
def media_deleted(sender, instance, **kwargs):
  try:
    _recalculate(instance.location)
  except Exception:
    pass  # location may have been deleted (CASCADE)


# ------------------------------------------------------------------ #
#  Comments (GenericRelation — resolve location via content_object)
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.Comment')
def comment_saved(sender, instance, raw, **kwargs):
  if raw:
    return
  from locations.models import Location
  if isinstance(instance.content_object, Location):
    _recalculate(instance.content_object)


@receiver(post_delete, sender='locations.Comment')
def comment_deleted(sender, instance, **kwargs):
  from locations.models import Location
  if isinstance(instance.content_object, Location):
    _recalculate(instance.content_object)


# ------------------------------------------------------------------ #
#  Through model: ListItem (Location.list_items)
# ------------------------------------------------------------------ #

@receiver(post_save, sender='locations.ListItem')
def listitem_saved(sender, instance, raw, **kwargs):
  if raw:
    return
  _recalculate(instance.location)


@receiver(post_delete, sender='locations.ListItem')
def listitem_deleted(sender, instance, **kwargs):
  _recalculate(instance.location)
