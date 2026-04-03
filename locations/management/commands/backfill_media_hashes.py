import hashlib

from django.core.management.base import BaseCommand

from locations.models.Media import Media


class Command(BaseCommand):
  help = 'Backfill SHA-256 file_hash for Media records that have none.'

  def handle(self, *args, **options):
    qs = Media.objects.filter(file_hash='')
    total = qs.count()

    if not total:
      self.stdout.write(self.style.SUCCESS('All media already have a hash.'))
      return

    self.stdout.write(f'Backfilling hashes for {total} media record(s)...')
    updated = 0
    skipped = 0

    for media in qs:
      try:
        media.source.open('rb')
        file_hash = hashlib.sha256(media.source.read()).hexdigest()
        media.source.close()
        Media.objects.filter(pk=media.pk).update(file_hash=file_hash)
        updated += 1
      except Exception as e:
        self.stdout.write(self.style.WARNING(f'  Skipped {media.pk} ({media.source.name}): {e}'))
        skipped += 1

    self.stdout.write(self.style.SUCCESS(f'Done. {updated} updated, {skipped} skipped.'))
