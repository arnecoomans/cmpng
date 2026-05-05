import datetime
import pytest
from unittest.mock import patch
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


# ------------------------------------------------------------------ #
#  upcoming() classmethod
#  Frozen date: 2026-05-05 (mid-year, no year-wrap in default window)
# ------------------------------------------------------------------ #

FROZEN_TODAY = datetime.date(2026, 5, 5)


def _freeze(fn):
  """Decorator: patch datetime.date.today → FROZEN_TODAY inside fn."""
  from functools import wraps
  @wraps(fn)
  def wrapper(*args, **kwargs):
    with patch('datetime.date') as MockDate:
      MockDate.today.return_value = FROZEN_TODAY
      return fn(*args, **kwargs)
  return wrapper


@pytest.mark.django_db
class TestVisitsUpcoming:

  def _user_and_location(self):
    user = UserFactory()
    location = LocationFactory()
    return user, location

  # ---- current month ------------------------------------------------

  def test_includes_current_month_no_day(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=5)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert qs.filter(year=2026, month=5).exists()

  def test_includes_current_month_on_today(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=5, day=5)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert qs.filter(year=2026, month=5, day=5).exists()

  def test_includes_current_month_after_today(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=5, day=20)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert qs.filter(year=2026, month=5, day=20).exists()

  def test_excludes_current_month_before_today(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=5, day=1)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2026, month=5, day=1).exists()

  # ---- future months within window ---------------------------------

  def test_includes_future_month_in_window(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=8)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert qs.filter(year=2026, month=8).exists()

  def test_excludes_month_beyond_window(self):
    # 6 months ahead of May → Nov (month 11); Dec is outside
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=12)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2026, month=12).exists()

  def test_excludes_past_month(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=3)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2026, month=3).exists()

  def test_excludes_past_year(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2025, month=9)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2025).exists()

  # ---- year-only visits --------------------------------------------

  def test_includes_year_only_in_current_year(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=None)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert qs.filter(year=2026, month__isnull=True).exists()

  def test_excludes_year_only_past_year(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2025, month=None)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2025, month__isnull=True).exists()

  # ---- year wrap (Oct → Apr next year) -----------------------------

  def test_year_wrap_includes_next_year_month(self):
    # Frozen: 2026-10-01; window: Oct–2026 to Apr-2027
    oct_today = datetime.date(2026, 10, 1)
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2027, month=2)
    with patch('datetime.date') as M:
      M.today.return_value = oct_today
      qs = Visits.upcoming(user)
    assert qs.filter(year=2027, month=2).exists()

  def test_year_wrap_excludes_month_beyond_window(self):
    # Frozen: 2026-10-01; window ends Apr-2027; May-2027 is outside
    oct_today = datetime.date(2026, 10, 1)
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2027, month=5)
    with patch('datetime.date') as M:
      M.today.return_value = oct_today
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2027, month=5).exists()

  # ---- status / visibility -----------------------------------------

  def test_excludes_revoked_visit(self):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=7, status='r')
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.filter(year=2026, month=7, status='r').exists()

  def test_excludes_other_users_visits(self):
    user, location = self._user_and_location()
    other = UserFactory()
    VisitsFactory(user=other, location=location, year=2026, month=7)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      qs = Visits.upcoming(user)
    assert not qs.exists()

  # ---- ordering & select_related -----------------------------------

  def test_ordered_by_year_month_day(self):
    user, _ = self._user_and_location()
    loc = LocationFactory()
    VisitsFactory(user=user, location=loc, year=2026, month=9, day=1)
    VisitsFactory(user=user, location=loc, year=2026, month=6, day=1)
    VisitsFactory(user=user, location=loc, year=2026, month=6, day=None)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      results = list(Visits.upcoming(user))
    years_months = [(v.year, v.month) for v in results]
    assert years_months == sorted(years_months, key=lambda x: (x[0], x[1] or 0))

  def test_location_accessible_without_extra_query(self, django_assert_num_queries):
    user, location = self._user_and_location()
    VisitsFactory(user=user, location=location, year=2026, month=7)
    with patch('datetime.date') as M:
      M.today.return_value = FROZEN_TODAY
      with django_assert_num_queries(1):
        visits = list(Visits.upcoming(user))
        _ = visits[0].location.name
