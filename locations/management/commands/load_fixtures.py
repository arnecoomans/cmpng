from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

# Fixtures handled by dedicated management commands, not loaddata.
SKIP_FILES = {
  'summaries.json',  # loaded by load_summaries
  'fixture_users.json',  # created by create_fixture_users
}

# Fixtures that must load in a specific order due to FK dependencies.
# Any fixture file not listed here loads alphabetically after these.
LOAD_ORDER = [
  'users.json',
  'regions.json',
  'categories.json',
  'tags.json',
  'chains.json',
  'sizes.json',
  'locations.json',
  'links.json',
  'media.json',
  'visits.json',
  'distances.json',
  'lists.json',
]


class Command(BaseCommand):
  help = 'Run loaddata for every JSON fixture in locations/fixtures/, respecting dependency order.'

  def add_arguments(self, parser):
    parser.add_argument(
      '--dir',
      default=None,
      help='Path to fixtures directory (default: locations/fixtures/)',
    )

  def handle(self, *args, **options):
    fixtures_dir = Path(options['dir']) if options['dir'] else (
      Path(__file__).resolve().parents[2] / 'fixtures'
    )

    if not fixtures_dir.exists():
      self.stdout.write(self.style.ERROR(f'Directory not found: {fixtures_dir}'))
      return

    all_files = {f.name: f for f in fixtures_dir.glob('*.json')}
    if not all_files:
      self.stdout.write(self.style.WARNING(f'No JSON fixtures found in {fixtures_dir}'))
      return

    # Create fixture users before loading
    self.stdout.write('Creating fixture users...')
    call_command('create_fixture_users', verbosity=0)
    self.stdout.write(self.style.SUCCESS('  Done.\n'))

    # Build ordered list: known order first, then remaining files alphabetically.
    # Files in SKIP_FILES are excluded — they are handled by dedicated commands.
    ordered = [all_files[name] for name in LOAD_ORDER if name in all_files]
    remaining = sorted(f for name, f in all_files.items() if name not in LOAD_ORDER and name not in SKIP_FILES)
    files = ordered + remaining

    self.stdout.write(f'Loading {len(files)} fixture(s) from {fixtures_dir}\n')

    for fixture in files:
      self.stdout.write(f'  → {fixture.name} ... ', ending='')
      try:
        call_command('loaddata', str(fixture), verbosity=0)
        self.stdout.write(self.style.SUCCESS('OK'))
      except Exception as e:
        self.stdout.write(self.style.ERROR(f'FAILED: {e}'))

    # Saving all regions
    self.stdout.write('\nSaving all regions to trigger signals...')
    from locations.models import Region
    for region in Region.objects.all():
      region.save()
    self.stdout.write(self.style.SUCCESS('  Done.\n'))
    
    # Apply summaries
    self.stdout.write('\nApplying summaries...')
    call_command('load_summaries', verbosity=0)
    self.stdout.write(self.style.SUCCESS('  Done.\n'))

    # Calculate distances after all fixtures are loaded
    self.stdout.write('\nCalculating distances...')
    call_command('calculate_distances', verbosity=0)
    self.stdout.write(self.style.SUCCESS('  Done.\n'))

    self.stdout.write(self.style.SUCCESS('\nDone.'))
