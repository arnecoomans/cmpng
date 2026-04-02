from django.core.management.base import BaseCommand

from locations.models.Location import Location


class Command(BaseCommand):
  help = 'Backfill completeness scores for all locations'

  def handle(self, *args, **options):
    locations = Location.objects.prefetch_related(
      'categories', 'links', 'visitors', 'list_items'
    )
    total = locations.count()
    self.stdout.write(f'Updating completeness for {total} locations...')
    for location in locations:
      location.calculate_completeness()
    self.stdout.write(self.style.SUCCESS(f'Done. {total} locations updated.'))
