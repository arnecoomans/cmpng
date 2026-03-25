from django.core.management.base import BaseCommand
from locations.models import Location, Region

class Command(BaseCommand):
  help = 'Calculate distances for all locations and regions'

  def add_arguments(self, parser):
    parser.add_argument(
      '--force',
      action='store_true',
      help='Recalculate even if distance already cached',
    )

  def handle(self, *args, **options):
    force = options['force']

    # Save all regions bottom-up so cascading fields are set before distances are calculated
    self.stdout.write('Saving all regions...')
    for level in ('department', 'region', 'country'):
      regions = Region.objects.filter(level=level)
      for region in regions:
        region.save()
      self.stdout.write(f'  {regions.count()} {level}(s) saved')

    # Calculate location distances
    locations = Location.objects.filter(status='p')
    if not force:
      locations = locations.filter(distance_to_departure_center__isnull=True)
    
    total = locations.count()
    self.stdout.write(f'Calculating distances for {total} locations...')
    
    for i, location in enumerate(locations, 1):
      if location.coord_lat and location.coord_lon:
        distance = location.calculate_distance_to_departure_center()
        if distance:
          self.stdout.write(f'  [{i}/{total}] {location.name}: {distance} km')
        else:
          self.stdout.write(f'  [{i}/{total}] {location.name}: Could not calculate')
      else:
        self.stdout.write(f'  [{i}/{total}] {location.name}: No coordinates')
    
    # Recalculate region averages (starting from departments up to countries)
    self.stdout.write('\nRecalculating region averages...')
    
    # Start with departments (level 2)
    departments = Region.objects.filter(level='department', status='p')
    for dept in departments:
      avg = dept.calculate_average_distance_to_center()
      if avg:
        self.stdout.write(f'  {dept.name}: {avg:.1f} km average')
    
    self.stdout.write(self.style.SUCCESS('\nDistance calculation complete!'))