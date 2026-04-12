from django.db.models import Avg

from locations.models.Visits import Visits

VISIT_STATE_NONE = 'none'
VISIT_STATE_OTHERS_POS = 'others-pos'
VISIT_STATE_OTHERS_NEU = 'others-neu'
VISIT_STATE_OTHERS_NEG = 'others-neg'
VISIT_STATE_YOU_POS = 'you-pos'
VISIT_STATE_YOU_NEU = 'you-neu'
VISIT_STATE_YOU_NEG = 'you-neg'


def _score_to_bucket(score):
  """Convert a community average score (float|None) to a color bucket string.

  Args:
    score: Average recommendation score, or None when no rated visits exist.

  Returns:
    'pos' (score > 0), 'neg' (score < 0), or 'neu' (zero or no data).
  """
  if score is None or score == 0.0:
    return 'neu'
  return 'pos' if score > 0 else 'neg'


def get_visit_context(location, user):
  """Return all visit-related context vars for a single location.

  Performs 2–3 DB queries. Use with_visit_state() annotation on list views.

  Args:
    location: Location instance.
    user: User instance (may be unauthenticated).

  Returns:
    Dict with keys:
      visit_state (str): CSS modifier — one of the VISIT_STATE_* constants.
      visit_user_recommendation (int|None): user's own recommendation value, or None.
      visit_community_score (float|None): average rated score, or None if unrated.
  """
  anyone_visited = Visits.objects.filter(location=location, status='p').exists()

  if not anyone_visited:
    return {
      'visit_state': VISIT_STATE_NONE,
      'visit_user_recommendation': None,
      'visit_community_score': None,
    }

  # Two-level average: each user gets one vote regardless of visit count
  user_avgs_qs = (
    Visits.objects
    .filter(location=location, recommendation__isnull=False, status='p')
    .values('user')
    .annotate(user_avg=Avg('recommendation'))
  )
  community_score_raw = user_avgs_qs.aggregate(avg=Avg('user_avg'))['avg']
  community_score = round(community_score_raw, 2) if community_score_raw is not None else None

  bucket = _score_to_bucket(community_score)

  if not getattr(user, 'is_authenticated', False):
    return {
      'visit_state': f'others-{bucket}',
      'visit_user_recommendation': None,
      'visit_community_score': community_score,
    }

  user_visit = (
    Visits.objects
    .filter(location=location, user=user, status='p')
    .order_by('-year', '-month', '-day')
    .first()
  )

  if user_visit is None:
    return {
      'visit_state': f'others-{bucket}',
      'visit_user_recommendation': None,
      'visit_community_score': community_score,
    }

  return {
    'visit_state': f'you-{bucket}',
    'visit_user_recommendation': user_visit.recommendation,
    'visit_community_score': community_score,
  }


def get_visit_state(location, user):
  """Return the visit state string for a location and user.

  Convenience wrapper around get_visit_context().

  Args:
    location: Location instance.
    user: User instance (may be unauthenticated).

  Returns:
    One of: 'none', 'others-pos', 'others-neu', 'others-neg',
            'you-pos', 'you-neu', 'you-neg'
  """
  return get_visit_context(location, user)['visit_state']


def visit_state_from_annotation(location):
  """Derive visit state from annotations added by LocationQuerySet.with_visit_state().

  Expects location to have visit_anyone_visited (bool), visit_user_visited (bool),
  and visit_community_score (float|None) annotations.

  Args:
    location: Location instance with visit_* annotations.

  Returns:
    One of: 'none', 'others-pos', 'others-neu', 'others-neg',
            'you-pos', 'you-neu', 'you-neg'
  """
  if not getattr(location, 'visit_anyone_visited', False):
    return VISIT_STATE_NONE

  community_score = getattr(location, 'visit_community_score', None)
  bucket = _score_to_bucket(community_score)

  if not getattr(location, 'visit_user_visited', False):
    return f'others-{bucket}'

  return f'you-{bucket}'


def get_recommendation_summary(location):
  """Return recommendation counts and average score for a location.

  Args:
    location: Location instance to summarise.

  Returns:
    Dict with keys:
      recommend (int): visits with recommendation=1
      neutral (int): visits with recommendation=0
      do_not_recommend (int): visits with recommendation=-1
      score (float|None): average of rated visits (-1.0 to 1.0), or None if no rated visits
  """
  # Per-user averages: each user gets one vote regardless of visit count
  user_avgs = list(
    Visits.objects
    .filter(location=location, recommendation__isnull=False, status='p')
    .values('user')
    .annotate(u=Avg('recommendation'))
    .values_list('u', flat=True)
  )

  counts = {1: 0, 0: 0, -1: 0}
  for avg in user_avgs:
    counts[1 if avg > 0 else (-1 if avg < 0 else 0)] += 1

  total = len(user_avgs)
  score = round(sum(user_avgs) / total, 2) if total else None

  return {
    'recommend': counts[Visits.RECOMMENDATION_RECOMMEND],
    'neutral': counts[Visits.RECOMMENDATION_NEUTRAL],
    'do_not_recommend': counts[Visits.RECOMMENDATION_DO_NOT_RECOMMEND],
    'score': score,
  }
