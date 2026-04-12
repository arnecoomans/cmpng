from django.conf import settings


# Bonus added to the base tag/category overlap score.
# These allow chain/size/recommendation signals to close the gap to
# min_overlap but cannot substitute for tag/category overlap entirely —
# a location with zero attribute overlap never reaches the threshold.
_CHAIN_SAME_BONUS    = 0.20  # exact same chain (e.g. all Huttopias)
_CHAIN_ANY_BONUS     = 0.05  # both belong to a chain, regardless of which
_SIZE_SAME_BONUS     = 0.10  # identical size classification
_SIZE_ADJACENT_BONUS = 0.05  # one step apart in size order
_RECOMMENDATION_BONUS = 0.10 # positive community recommendation score
_FAVORITE_BONUS       = 0.05 # at least one user has favorited this location


def _chain_bonus(ref_chain_id, cand_chain_id):
  """Return chain similarity bonus (0, 0.05, or 0.20)."""
  if not ref_chain_id or not cand_chain_id:
    return 0.0
  if ref_chain_id == cand_chain_id:
    return _CHAIN_SAME_BONUS
  return _CHAIN_ANY_BONUS


def _size_bonus(ref_size, cand_size):
  """Return size proximity bonus (0, 0.05, or 0.10).

  Compares Size.order values; requires both sizes to be set.
  """
  if ref_size is None or cand_size is None:
    return 0.0
  diff = abs(ref_size.order - cand_size.order)
  if diff == 0:
    return _SIZE_SAME_BONUS
  if diff == 1:
    return _SIZE_ADJACENT_BONUS
  return 0.0


def get_similar_locations(location, min_overlap=None, max_results=None, queryset=None):
  """Return globally recommended locations with sufficient attribute overlap.

  The composite similarity score is:

    base           = Σ weight(shared tags) + Σ weight(shared cats) / Σ weight(all ref tags+cats)
                     tag weights come from Tag.similarity_weight (default 100); categories use 100
    chain          = +0.20 (same chain), +0.05 (both chained, different chain)
    size           = +0.10 (same size),  +0.05 (adjacent size)
    recommendation = +0.10 (positive community score), +0 (unrated or negative)
    favorite       = +0.05 (at least one user has favorited this location)
    score          = base + chain + size + recommendation + favorite

  Recommendation boosts ranking but is not required — unrated and negatively
  rated locations are included if their attribute overlap is sufficient.

  Each returned instance has a .similarity attribute (float, composite score).

  Args:
    location:    Reference Location instance.
    min_overlap: Minimum composite score (0–1+). Falls back to
                 settings.SIMILAR_OVERLAP_THRESHOLD or 0.3.
    max_results: Maximum number of results. Falls back to
                 settings.SIMILAR_MAX_RESULTS or 10.
    queryset:    Optional base queryset. Defaults to published locations
                 annotated with visit state (anonymous user).
                 When settings.SIMILAR_SAME_COUNTRY is True (default),
                 candidates are restricted to the same country.

  Returns:
    List[Location] sorted by score descending, then name ascending.
    Empty list when the reference location has no tags or categories.
  """
  from locations.models import Location

  min_overlap = min_overlap if min_overlap is not None else float(
    getattr(settings, 'SIMILAR_OVERLAP_THRESHOLD', 0.3)
  )
  max_results = max_results if max_results is not None else int(
    getattr(settings, 'SIMILAR_MAX_RESULTS', 10)
  )

  # Build weighted maps: {pk: weight}. Categories have uniform weight 100.
  ref_tag_weights = dict(location.tags.values_list('pk', 'similarity_weight'))
  ref_cat_weights = {pk: 100 for pk in location.categories.values_list('pk', flat=True)}
  total = sum(ref_tag_weights.values()) + sum(ref_cat_weights.values())

  if total == 0:
    return []

  ref_chain_id = location.chain_id
  ref_size = location.size  # may be None; Size.order accessed below
  same_country = getattr(settings, 'SIMILAR_SAME_COUNTRY', True)

  if queryset is None:
    from django.contrib.auth.models import AnonymousUser
    queryset = (
      Location.objects
      .filter(status='p')
      .with_visit_state(AnonymousUser())
      .select_related('chain', 'size')
      .prefetch_related('tags', 'categories', 'favorited')
    )

  candidates = queryset.exclude(pk=location.pk)
  if same_country and location.country:
    candidates = candidates.filter(geo__parent__parent=location.country)

  results = []
  for candidate in candidates:
    cand_tag_pks = frozenset(t.pk for t in candidate.tags.all())
    cand_cat_pks = frozenset(c.pk for c in candidate.categories.all())
    shared_weight = (
      sum(w for pk, w in ref_tag_weights.items() if pk in cand_tag_pks) +
      sum(ref_cat_weights[pk] for pk in ref_cat_weights if pk in cand_cat_pks)
    )
    base = shared_weight / total

    rec_bonus = _RECOMMENDATION_BONUS if (getattr(candidate, 'visit_community_score', None) or 0) > 0 else 0.0
    fav_bonus = _FAVORITE_BONUS if candidate.favorited.all() else 0.0

    score = (
      base
      + _chain_bonus(ref_chain_id, candidate.chain_id)
      + _size_bonus(ref_size, candidate.size)
      + rec_bonus
      + fav_bonus
    )

    if score >= min_overlap:
      candidate.similarity = round(score, 2)
      results.append(candidate)

  results.sort(key=lambda loc: (-loc.similarity, loc.name))
  return results[:max_results]
