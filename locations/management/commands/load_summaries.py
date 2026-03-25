import json
from pathlib import Path

from django.core.management.base import BaseCommand

from locations.models import Location


class Command(BaseCommand):
  help = 'Apply summaries from fixtures/summaries.json to existing Location records.'

  def add_arguments(self, parser):
    parser.add_argument(
      '--fixture',
      default=None,
      help='Path to summaries fixture (default: locations/fixtures/summaries.json)',
    )

  def handle(self, *args, **options):
    fixture_path = Path(options['fixture']) if options['fixture'] else (
      Path(__file__).resolve().parents[2] / 'fixtures' / 'summaries.json'
    )

    if not fixture_path.exists():
      self.stdout.write(self.style.ERROR(f'Fixture not found: {fixture_path}'))
      return

    with open(fixture_path) as f:
      data = json.load(f)

    updated = 0
    skipped = 0

    for item in data:
      pk = item['pk']
      summary = item['fields']['summary']
      count = Location.objects.filter(pk=pk).update(summary=summary)
      if count:
        updated += 1
      else:
        skipped += 1
        self.stdout.write(self.style.WARNING(f'  pk={pk} not found, skipped'))

    self.stdout.write(self.style.SUCCESS(f'Done. {updated} updated, {skipped} skipped.'))
