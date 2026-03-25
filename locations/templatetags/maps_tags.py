from django import template

register = template.Library()

SESSION_KEY = 'external_maps_consent'
REQUEST_PARAM = 'external_maps_consent'


def _save_preference(request):
  """Persist maps consent to user.preferences. Silently skips if unavailable."""
  try:
    prefs = request.user.preferences
    if not prefs.external_maps_consent:
      prefs.external_maps_consent = True
      prefs.save(update_fields=['external_maps_consent'])
  except Exception:
    pass


@register.simple_tag(takes_context=True)
def has_maps_consent(context):
  """
  Check if the user has consented to loading external maps.

  Priority order:
  1. ?external_maps_consent=once    — allow for this view only, no storage
  2. ?external_maps_consent=session — allow and save to session
  3. ?external_maps_consent=always  — allow and save to user.preferences (authenticated only)
  4. Session key
  5. user.preferences.external_maps_consent

  Returns True if consent is granted, False otherwise.
  """
  request = context.get('request')
  if not request:
    return False

  param = request.GET.get(REQUEST_PARAM, '').lower()

  if param == 'once':
    return True

  if param == 'session':
    request.session[SESSION_KEY] = True
    return True

  if param == 'always':
    if request.user.is_authenticated:
      _save_preference(request)
    else:
      request.session[SESSION_KEY] = True
    return True

  if request.session.get(SESSION_KEY):
    return True

  if request.user.is_authenticated:
    try:
      if request.user.preferences.external_maps_consent:
        return True
    except Exception:
      pass

  return False
