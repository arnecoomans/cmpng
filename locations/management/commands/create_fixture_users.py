import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

# Sensitive data (password hashes, emails) lives in a gitignored secrets file.
# See locations/fixtures/fixture_users.json.example for the expected format.
SECRETS_FILE = Path(__file__).resolve().parents[2] / 'fixtures' / 'fixture_users.json'


class Command(BaseCommand):
  help = 'Create fixture users for development'

  def add_arguments(self, parser):
    parser.add_argument(
      '--reset-passwords',
      action='store_true',
      help='Reset passwords for existing users too',
    )

  def handle(self, *_args, **options):
    reset_passwords = options['reset_passwords']

    secrets = self._load_secrets()
    if not secrets:
      self.stdout.write(self.style.WARNING(
        f'No secrets file found at {SECRETS_FILE}. '
        'Users will be created with unusable passwords.'
      ))

    users = [
      {'pk': 1, 'username': 'arnecoomans',  'first_name': 'Arne',   'last_name': 'Coomans',    'is_staff': True,  'is_superuser': True},
      {'pk': 2, 'username': 'ingecoomans',   'first_name': 'Inge',   'last_name': 'Coomans',    'is_staff': True,  'is_superuser': False},
      {'pk': 3, 'username': 'sandracoomans', 'first_name': 'Sandra', 'last_name': 'Coomans',    'is_staff': False, 'is_superuser': False},
      {'pk': 4, 'username': 'morice',        'first_name': 'Morice', 'last_name': 'Koningstein','is_staff': False, 'is_superuser': False},
    ]

    for user_data in users:
      pk       = user_data.pop('pk')
      username = user_data['username']
      user_secrets = secrets.get(username, {})

      if 'email' in user_secrets:
        user_data['email'] = user_secrets['email']

      try:
        user = User.objects.get(pk=pk)
        created = False
      except User.DoesNotExist:
        try:
          user = User.objects.get(username=username)
          created = False
        except User.DoesNotExist:
          user = User(pk=pk, **user_data)
          created = True

      if created or reset_passwords:
        if 'password_hash' in user_secrets:
          user.password = user_secrets['password_hash']
        else:
          user.set_unusable_password()
        user.save()
        status = 'Created' if created else 'Updated password for'
        self.stdout.write(self.style.SUCCESS(f'{status} user: {username} (pk={pk})'))
      else:
        self.stdout.write(f'User already exists: {username} (pk={pk})')

  def _load_secrets(self):
    if not SECRETS_FILE.exists():
      return {}
    with SECRETS_FILE.open() as f:
      return json.load(f)
