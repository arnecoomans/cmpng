from django.conf import settings
from django.core.management.base import BaseCommand

from locations.models.Page import Page


SITE_NAME = getattr(settings, 'SITE_NAME', 'this site')

DEFAULT_PAGES = [
  {
    'slug': 'cookie-statement',
    'language': 'en',
    'title': 'Cookie statement',
    'body': f"""## Cookie statement

{SITE_NAME} uses cookies to provide its service.

### What cookies do we use?

- **Session cookie** — keeps you logged in during your visit. Removed when you close your browser.
- **Language cookie** — remembers your language preference across visits.
- **CSRF cookie** — protects form submissions against cross-site request forgery. Required for security.

### Privacy by design

To protect your privacy, all JavaScript libraries, CSS stylesheets, and fonts are hosted locally. No data is shared with commercial third parties simply by visiting {SITE_NAME}.

Before any information is shared with an external commercial service — such as the map view — your explicit consent is requested and recorded.

All personal information linked to your account can be viewed and managed from your [preferences page](/preferences/).

### What we do not do

{SITE_NAME} does not use tracking cookies or advertising cookies, and does not share data with third parties without your consent.

### Questions?

If you have any questions about how {SITE_NAME} handles your data, please get in touch.
""",
    'status': 'p',
    'visibility': 'p',
  },
  {
    'slug': 'cookie-statement',
    'language': 'nl',
    'title': 'Cookieverklaring',
    'body': f"""## Cookieverklaring

{SITE_NAME} maakt gebruik van cookies om de dienst te kunnen leveren.

### Welke cookies gebruiken we?

- **Sessiecookie** — houdt je ingelogd tijdens je bezoek. Wordt verwijderd als je de browser sluit.
- **Taalcookie** — onthoudt je taalvoorkeur voor volgende bezoeken.
- **CSRF-cookie** — beschermt formulieren tegen ongewenste verzoeken van buitenaf. Vereist voor beveiliging.

### Privacy by design

Ter bescherming van je privacy worden alle JavaScript-bibliotheken, CSS-stylesheets en lettertypen lokaal gehost. Er wordt geen data gedeeld met commerciële partijen enkel doordat je {SITE_NAME} bezoekt.

Voordat informatie wordt gedeeld met een externe commerciële dienst — zoals de kaartweergave — wordt je expliciete toestemming gevraagd en geregistreerd.

Alle persoonlijke gegevens die aan je account zijn gekoppeld, kun je bekijken en beheren via je [voorkeuren pagina](/preferences/).

### Wat we niet doen

{SITE_NAME} gebruikt geen tracking- of advertentiecookies en deelt geen gegevens met derden zonder jouw toestemming.

### Vragen?

Heb je vragen over hoe {SITE_NAME} omgaat met jouw gegevens? Neem dan contact op.
""",
    'status': 'p',
    'visibility': 'p',
  },
  {
    'slug': 'cookie-statement',
    'language': 'fr',
    'title': 'Politique de cookies',
    'body': f"""## Politique de cookies

{SITE_NAME} utilise des cookies pour fournir son service.

### Quels cookies utilisons-nous ?

- **Cookie de session** — vous maintient connecté pendant votre visite. Supprimé à la fermeture du navigateur.
- **Cookie de langue** — mémorise votre préférence de langue pour vos prochaines visites.
- **Cookie CSRF** — protège les formulaires contre les requêtes malveillantes. Obligatoire pour la sécurité.

### Protection de la vie privée

Pour protéger votre vie privée, toutes les bibliothèques JavaScript, feuilles de style CSS et polices de caractères sont hébergées localement. Aucune donnée n'est partagée avec des entités commerciales simplement en visitant {SITE_NAME}.

Avant tout partage d'informations avec un service commercial externe — comme l'affichage de la carte — votre consentement explicite est demandé et enregistré.

Toutes les informations personnelles liées à votre compte peuvent être consultées et gérées depuis votre [page de préférences](/preferences/).

### Ce que nous ne faisons pas

{SITE_NAME} n'utilise pas de cookies de suivi ou publicitaires et ne partage aucune donnée avec des tiers sans votre consentement.

### Questions ?

Pour toute question concernant la gestion de vos données par {SITE_NAME}, n'hésitez pas à nous contacter.
""",
    'status': 'p',
    'visibility': 'p',
  },
]


class Command(BaseCommand):
  help = 'Seed default pages (idempotent — skips pages that already exist)'

  def handle(self, *_args, **_options):
    created_count = 0
    for page_data in DEFAULT_PAGES:
      slug = page_data['slug']
      language = page_data['language']
      if Page.objects.filter(slug=slug, language=language).exists():
        self.stdout.write(f'Skipped (already exists): {slug}/{language}')
        continue
      Page.objects.create(**page_data)
      self.stdout.write(self.style.SUCCESS(f'Created page: {slug}/{language}'))
      created_count += 1

    if created_count:
      self.stdout.write(self.style.SUCCESS(f'{created_count} page(s) created.'))
    else:
      self.stdout.write('No new pages created.')
