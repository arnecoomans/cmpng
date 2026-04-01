from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


APP_LABEL = 'locations'

# Explicit codenames per group.
# community-member-read and community-member stack: a normal user gets both.
# Downgrade to read-only by removing community-member.
# Staff get all three groups.
GROUP_DEFINITIONS = {
  'community-member-read': [
    'view_location', 'view_tag', 'view_comment', 'view_link',
    'view_category', 'view_chain', 'view_list', 'view_listitem',
    'view_media', 'view_page', 'view_size', 'view_visits',
    'view_userpreferences',
  ],
  'community-member': [
    'add_location',  'change_location',
    'add_link',      'change_link',
                     'change_category',
    'add_chain',     'change_chain',
    'add_list',      'change_list',
    'add_listitem',  'change_listitem',
    'add_media',     'change_media',
                     'change_size',
    'add_visits',    'change_visits',
                     'change_userpreferences',
  ],
  'staff': [
    'add_category',    'change_category',
    'add_page',        'change_page',
    'add_size',        'change_size',
    'add_tag',         'change_tag',
    'add_region',      'change_region',
    'delete_location',                   # re-enrich and revoke actions
  ],
}


def create_groups(stdout=None):
  for name, codenames in GROUP_DEFINITIONS.items():
    group, created = Group.objects.get_or_create(name=name)
    perms = list(
      Permission.objects.filter(
        content_type__app_label=APP_LABEL,
        codename__in=codenames,
      )
    )
    group.permissions.set(perms)
    status = 'Created' if created else 'Updated'
    if stdout:
      stdout.write(f'{status} group "{name}" with {len(perms)} permission(s).')


class Command(BaseCommand):
  help = 'Create or update permission groups (idempotent)'

  def add_arguments(self, parser):
    parser.add_argument(
      '--sync-users',
      action='store_true',
      help='Assign default groups to all existing users who are missing them',
    )

  def handle(self, *_args, **options):
    create_groups(stdout=self.stdout)

    if options['sync_users']:
      read_group   = Group.objects.get(name='community-member-read')
      member_group = Group.objects.get(name='community-member')
      staff_group  = Group.objects.get(name='staff')

      User = get_user_model()
      synced = 0
      for user in User.objects.all():
        user_groups = user.groups.values_list('name', flat=True)
        if user.is_staff and 'staff' not in user_groups:
          user.groups.add(staff_group)
        if 'community-member-read' not in user_groups:
          user.groups.add(read_group)
        if 'community-member' not in user_groups:
          user.groups.add(member_group)
          synced += 1
          self.stdout.write(f'  Synced: {user.username}')

      self.stdout.write(self.style.SUCCESS(f'{synced} user(s) synced.'))

    self.stdout.write(self.style.SUCCESS('Done.'))
