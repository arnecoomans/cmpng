from django.core.management.base import BaseCommand

from locations.models import Category, Tag


class Command(BaseCommand):
  help = (
    'Refresh translation aliases on all Category and Tag objects. '
    'Run this after compilemessages to keep aliases in sync with .po files.'
  )

  def add_arguments(self, parser):
    parser.add_argument(
      '--dry-run',
      action='store_true',
      help='Show what would be updated without saving.',
    )

  def handle(self, *args, **options):
    dry_run = options['dry_run']
    updated = 0

    for model in (Category, Tag):
      name = model.__name__
      for obj in model.objects.all():
        old = obj.aliases
        obj._update_aliases()
        if obj.aliases != old:
          if not dry_run:
            model.objects.filter(pk=obj.pk).update(aliases=obj.aliases)
          self.stdout.write(
            f'  {name} "{obj.name}": "{old}" → "{obj.aliases}"'
          )
          updated += 1

    action = 'Would update' if dry_run else 'Updated'
    self.stdout.write(self.style.SUCCESS(f'{action} {updated} object(s).'))
