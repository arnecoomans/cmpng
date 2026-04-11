import pytest
from django.core.exceptions import ValidationError

from locations.models.Visits import Visits
from locations.tests.factories import UserFactory, LocationFactory, VisitsFactory


# ------------------------------------------------------------------ #
#  Months helper
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitsMonths:

  def test_get_months_returns_all_12(self):
    assert len(Visits.get_months()) == 12

  def test_get_months_first_is_january(self):
    assert Visits.get_months()[0][0] == 1

  def test_get_months_last_is_december(self):
    assert Visits.get_months()[-1][0] == 12


# ------------------------------------------------------------------ #
#  __str__
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitsStr:

  def test_str_single_year(self):
    user = UserFactory()
    location = LocationFactory(name='Camping Paradise')
    visit = VisitsFactory(user=user, location=location, year=2023)
    assert '2023' in str(visit)
    assert location.name in str(visit)

  def test_str_date_range(self):
    user = UserFactory()
    location = LocationFactory(name='Camping Paradise')
    visit = VisitsFactory(user=user, location=location, year=2022, end_year=2023)
    assert '2022' in str(visit)
    assert '2023' in str(visit)


# ------------------------------------------------------------------ #
#  nights()
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitsNights:

  def test_nights_returns_none_without_end_year(self):
    visit = VisitsFactory(year=2024)
    assert visit.nights() is None

  def test_nights_calculates_correctly(self):
    visit = VisitsFactory(
      year=2024, month=7, day=1,
      end_year=2024, end_month=7, end_day=8,
    )
    assert visit.nights() == 7

  def test_nights_returns_none_when_end_before_start(self):
    visit = VisitsFactory(
      year=2024, month=7, day=10,
      end_year=2024, end_month=7, end_day=8,
    )
    assert visit.nights() is None


# ------------------------------------------------------------------ #
#  clean() — date validation
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitsClean:

  def test_end_year_before_start_year_raises(self):
    visit = VisitsFactory.build(year=2024, end_year=2023)
    with pytest.raises(ValidationError) as exc:
      visit.clean()
    assert 'end_year' in exc.value.message_dict

  def test_end_month_before_start_month_same_year_raises(self):
    visit = VisitsFactory.build(year=2024, month=8, end_year=2024, end_month=6)
    with pytest.raises(ValidationError) as exc:
      visit.clean()
    assert 'end_month' in exc.value.message_dict

  def test_end_day_before_start_day_same_month_raises(self):
    visit = VisitsFactory.build(
      year=2024, month=7, day=15,
      end_year=2024, end_month=7, end_day=10,
    )
    with pytest.raises(ValidationError) as exc:
      visit.clean()
    assert 'end_day' in exc.value.message_dict

  def test_valid_date_range_does_not_raise(self):
    visit = VisitsFactory.build(
      year=2024, month=7, day=1,
      end_year=2024, end_month=7, end_day=8,
    )
    visit.clean()  # should not raise


# ------------------------------------------------------------------ #
#  recommendation field
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestVisitsRecommendation:

  def test_recommendation_defaults_to_null(self):
    visit = VisitsFactory()
    assert visit.recommendation is None

  def test_recommendation_accepts_recommend(self):
    visit = VisitsFactory(recommendation=Visits.RECOMMENDATION_RECOMMEND)
    assert visit.recommendation == 1

  def test_recommendation_accepts_neutral(self):
    visit = VisitsFactory(recommendation=Visits.RECOMMENDATION_NEUTRAL)
    assert visit.recommendation == 0

  def test_recommendation_accepts_do_not_recommend(self):
    visit = VisitsFactory(recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    assert visit.recommendation == -1

  def test_recommendation_constants_are_correct(self):
    assert Visits.RECOMMENDATION_RECOMMEND == 1
    assert Visits.RECOMMENDATION_NEUTRAL == 0
    assert Visits.RECOMMENDATION_DO_NOT_RECOMMEND == -1

  def test_recommendation_choices_cover_all_values(self):
    values = [choice[0] for choice in Visits.RECOMMENDATION_CHOICES]
    assert 1 in values
    assert 0 in values
    assert -1 in values

  def test_multiple_visits_can_have_different_recommendations(self):
    location = LocationFactory()
    user = UserFactory()
    v1 = VisitsFactory(user=user, location=location, year=2022, recommendation=Visits.RECOMMENDATION_RECOMMEND)
    v2 = VisitsFactory(user=user, location=location, year=2023, recommendation=Visits.RECOMMENDATION_DO_NOT_RECOMMEND)
    assert v1.recommendation != v2.recommendation

  def test_recommendation_persists_to_db(self):
    visit = VisitsFactory(recommendation=Visits.RECOMMENDATION_RECOMMEND)
    visit.refresh_from_db()
    assert visit.recommendation == Visits.RECOMMENDATION_RECOMMEND
