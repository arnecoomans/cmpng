import pytest

from locations.models.Visits import Visits
from locations.models.Location import Location
from locations.tests.factories import UserFactory, LocationFactory, VisitsFactory
from locations.services.visits_recommendation import (
  get_recommendation_summary,
  get_visit_state,
  get_visit_context,
  visit_state_from_annotation,
)


# ------------------------------------------------------------------ #
#  get_recommendation_summary
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetRecommendationSummary:

  def test_returns_dict_with_expected_keys(self):
    location = LocationFactory()
    result = get_recommendation_summary(location)
    assert 'recommend' in result
    assert 'neutral' in result
    assert 'do_not_recommend' in result
    assert 'score' in result

  def test_all_zero_when_no_visits(self):
    location = LocationFactory()
    result = get_recommendation_summary(location)
    assert result['recommend'] == 0
    assert result['neutral'] == 0
    assert result['do_not_recommend'] == 0

  def test_score_is_none_when_no_visits(self):
    location = LocationFactory()
    result = get_recommendation_summary(location)
    assert result['score'] is None

  def test_score_is_none_when_all_unrated(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=None)
    VisitsFactory(location=location, recommendation=None)
    result = get_recommendation_summary(location)
    assert result['score'] is None

  def test_counts_recommend_correctly(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    result = get_recommendation_summary(location)
    assert result['recommend'] == 2
    assert result['do_not_recommend'] == 1
    assert result['neutral'] == 0

  def test_counts_neutral_correctly(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_NEUTRAL)
    result = get_recommendation_summary(location)
    assert result['neutral'] == 1

  def test_unrated_visits_excluded_from_counts(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=None)
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    result = get_recommendation_summary(location)
    assert result['recommend'] == 1
    assert result['neutral'] == 0
    assert result['do_not_recommend'] == 0

  def test_score_is_1_when_all_recommend(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    result = get_recommendation_summary(location)
    assert result['score'] == 1.0

  def test_score_is_minus_1_when_all_do_not_recommend(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    result = get_recommendation_summary(location)
    assert result['score'] == -1.0

  def test_score_is_0_when_balanced(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    result = get_recommendation_summary(location)
    assert result['score'] == 0.0

  def test_score_excludes_unrated_visits(self):
    location = LocationFactory()
    VisitsFactory(location=location, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, recommendation=None)
    result = get_recommendation_summary(location)
    assert result['score'] == 1.0

  def test_only_counts_visits_for_given_location(self):
    location_a = LocationFactory()
    location_b = LocationFactory()
    VisitsFactory(location=location_a, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location_b, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    result = get_recommendation_summary(location_a)
    assert result['recommend'] == 1
    assert result['do_not_recommend'] == 0


# ------------------------------------------------------------------ #
#  get_visit_state / get_visit_context
#
#  State encodes: who visited (none/others/you) + community score bucket (pos/neu/neg)
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestGetVisitState:

  def test_returns_none_when_nobody_visited(self):
    location = LocationFactory()
    user = UserFactory()
    assert get_visit_state(location, user) == 'none'

  def test_returns_others_neu_when_others_visited_unrated(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=None)
    assert get_visit_state(location, user) == 'others-neu'

  def test_returns_others_pos_when_others_visited_positively(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    assert get_visit_state(location, user) == 'others-pos'

  def test_returns_others_neg_when_others_visited_negatively(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    assert get_visit_state(location, user) == 'others-neg'

  def test_returns_you_neu_when_user_visited_no_community_rating(self):
    location = LocationFactory()
    user = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=None)
    assert get_visit_state(location, user) == 'you-neu'

  def test_returns_you_pos_when_community_positive(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_NEUTRAL)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    assert get_visit_state(location, user) == 'you-pos'

  def test_returns_you_neg_when_community_negative(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    assert get_visit_state(location, user) == 'you-neg'

  def test_conflict_you_neg_but_community_pos(self):
    """State = you-pos because community is positive, even if you personally rated negative."""
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    assert get_visit_state(location, user) == 'you-pos'

  def test_unauthenticated_user_returns_none_when_nobody_visited(self):
    from unittest.mock import MagicMock
    location = LocationFactory()
    user = MagicMock()
    user.is_authenticated = False
    assert get_visit_state(location, user) == 'none'

  def test_unauthenticated_user_returns_others_pos_when_positively_rated(self):
    from unittest.mock import MagicMock
    location = LocationFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    user = MagicMock()
    user.is_authenticated = False
    assert get_visit_state(location, user) == 'others-pos'

  def test_context_includes_user_recommendation(self):
    location = LocationFactory()
    user = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    ctx = get_visit_context(location, user)
    assert ctx['visit_user_recommendation'] == Visits.RECOMMENDATION_RECOMMEND

  def test_context_includes_community_score(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    ctx = get_visit_context(location, user)
    assert ctx['visit_community_score'] == 1.0

  def test_context_user_recommendation_none_for_others_state(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other)
    ctx = get_visit_context(location, user)
    assert ctx['visit_user_recommendation'] is None


# ------------------------------------------------------------------ #
#  visit_state_from_annotation
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitStateFromAnnotation:

  def _annotated(self, location, user):
    return Location.objects.with_visit_state(user).get(pk=location.pk)

  def test_state_is_none_when_nobody_visited(self):
    location = LocationFactory()
    user = UserFactory()
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'none'

  def test_state_is_others_neu_when_others_visited_unrated(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=None)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'others-neu'

  def test_state_is_others_pos_when_community_positive(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'others-pos'

  def test_state_is_others_neg_when_community_negative(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'others-neg'

  def test_state_is_you_neu_when_user_visited_no_ratings(self):
    location = LocationFactory()
    user = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=None)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'you-neu'

  def test_state_is_you_pos_when_community_positive(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_NEUTRAL)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'you-pos'

  def test_state_is_you_neg_when_community_negative(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    loc = self._annotated(location, user)
    assert visit_state_from_annotation(loc) == 'you-neg'

  def test_unauthenticated_user_gets_none_when_nobody_visited(self):
    from unittest.mock import MagicMock
    location = LocationFactory()
    user = MagicMock()
    user.is_authenticated = False
    user.pk = None
    loc = Location.objects.with_visit_state(user).get(pk=location.pk)
    assert visit_state_from_annotation(loc) == 'none'

  def test_unauthenticated_user_gets_others_pos_when_community_positive(self):
    from unittest.mock import MagicMock
    location = LocationFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    user = MagicMock()
    user.is_authenticated = False
    user.pk = None
    loc = Location.objects.with_visit_state(user).get(pk=location.pk)
    assert visit_state_from_annotation(loc) == 'others-pos'

  def test_annotation_includes_community_score(self):
    location = LocationFactory()
    user = UserFactory()
    other = UserFactory()
    VisitsFactory(location=location, user=other, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    loc = self._annotated(location, user)
    assert loc.visit_community_score == 1.0

  def test_community_score_is_none_when_no_rated_visits(self):
    location = LocationFactory()
    user = UserFactory()
    VisitsFactory(location=location, user=user, recommendation=None)
    loc = self._annotated(location, user)
    assert loc.visit_community_score is None
