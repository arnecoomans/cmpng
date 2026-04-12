import pytest
from locations.models import Location
from locations.services.location_similar import (
  get_similar_locations,
  _chain_bonus,
  _size_bonus,
  _CHAIN_SAME_BONUS,
  _CHAIN_ANY_BONUS,
  _SIZE_SAME_BONUS,
  _SIZE_ADJACENT_BONUS,
  _RECOMMENDATION_BONUS,
  _FAVORITE_BONUS,
)
from locations.tests.factories import (
  LocationFactory,
  CategoryFactory,
  TagFactory,
  ChainFactory,
  SizeFactory,
  RegionFactory,
  UserPreferencesFactory,
  VisitsFactory,
)


def make_region_hierarchy(country_name='Netherlands'):
  """Return (country, region, department) RegionFactory instances."""
  country = RegionFactory(name=country_name, parent=None)
  region = RegionFactory(parent=country)
  department = RegionFactory(parent=region)
  return country, region, department


# ================================================================
# Unit tests for bonus helpers
# ================================================================

class TestChainBonus:
  def test_same_chain(self):
    assert _chain_bonus(1, 1) == _CHAIN_SAME_BONUS

  def test_different_chains(self):
    assert _chain_bonus(1, 2) == _CHAIN_ANY_BONUS

  def test_ref_no_chain(self):
    assert _chain_bonus(None, 1) == 0.0

  def test_cand_no_chain(self):
    assert _chain_bonus(1, None) == 0.0

  def test_both_no_chain(self):
    assert _chain_bonus(None, None) == 0.0


class TestSizeBonus:
  def test_same_size(self):
    class S:
      def __init__(self, o): self.order = o
    assert _size_bonus(S(2), S(2)) == _SIZE_SAME_BONUS

  def test_adjacent_size(self):
    class S:
      def __init__(self, o): self.order = o
    assert _size_bonus(S(2), S(3)) == _SIZE_ADJACENT_BONUS
    assert _size_bonus(S(3), S(2)) == _SIZE_ADJACENT_BONUS

  def test_far_size(self):
    class S:
      def __init__(self, o): self.order = o
    assert _size_bonus(S(1), S(5)) == 0.0

  def test_ref_no_size(self):
    class S:
      def __init__(self, o): self.order = o
    assert _size_bonus(None, S(2)) == 0.0

  def test_cand_no_size(self):
    class S:
      def __init__(self, o): self.order = o
    assert _size_bonus(S(2), None) == 0.0


# ================================================================
# Integration tests for get_similar_locations
# ================================================================

@pytest.mark.django_db
class TestSimilarLocationsBasic:
  def setup_method(self):
    _, _, self.dept = make_region_hierarchy()
    self.cat_a = CategoryFactory()
    self.cat_b = CategoryFactory()
    self.tag_x = TagFactory()
    self.tag_y = TagFactory()

  def _loc(self, **kwargs):
    return LocationFactory(geo=self.dept, **kwargs)

  def test_returns_empty_when_no_tags_or_categories(self):
    ref = self._loc()
    self._loc()
    assert get_similar_locations(ref, min_overlap=0.0) == []

  def test_excludes_reference_location_itself(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert ref not in results

  def test_returns_location_with_shared_category(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    cand = self._loc()
    cand.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert cand in results

  def test_excludes_location_below_threshold(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    ref.categories.add(self.cat_b)
    # candidate shares only 1 of 2 → base = 0.5
    cand = self._loc()
    cand.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.9)
    assert cand not in results

  def test_excludes_unpublished_locations(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    cand = LocationFactory(geo=self.dept, status='c')
    cand.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert cand not in results

  def test_similarity_attribute_set_on_results(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    cand = self._loc()
    cand.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert hasattr(results[0], 'similarity')
    assert 0.0 < results[0].similarity <= 1.5  # can exceed 1.0 with bonuses

  def test_sorted_by_similarity_descending(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    ref.categories.add(self.cat_b)
    # high: shares both
    high = self._loc()
    high.categories.add(self.cat_a)
    high.categories.add(self.cat_b)
    # low: shares one
    low = self._loc()
    low.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0)
    pks = [r.pk for r in results]
    assert pks.index(high.pk) < pks.index(low.pk)

  def test_max_results_respected(self):
    ref = self._loc()
    ref.categories.add(self.cat_a)
    for _ in range(5):
      c = self._loc()
      c.categories.add(self.cat_a)
    results = get_similar_locations(ref, min_overlap=0.0, max_results=3)
    assert len(results) == 3

  def test_shared_tag_counts_toward_overlap(self):
    ref = self._loc()
    ref.tags.add(self.tag_x)
    cand = self._loc()
    cand.tags.add(self.tag_x)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert cand in results

  def test_base_score_is_weight_fraction(self):
    # ref has one tag with default weight 100; cand shares it → base = 100/100 = 1.0
    tag = TagFactory(similarity_weight=100)
    ref = self._loc()
    ref.tags.add(tag)
    cand = self._loc()
    cand.tags.add(tag)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == 1.0


@pytest.mark.django_db
class TestSimilarLocationsBonuses:
  def setup_method(self):
    _, _, self.dept = make_region_hierarchy()
    self.cat = CategoryFactory()

  def _loc(self, **kwargs):
    return LocationFactory(geo=self.dept, **kwargs)

  def test_same_chain_raises_score(self):
    chain = ChainFactory()
    ref = self._loc(chain=chain)
    ref.categories.add(self.cat)
    cand = self._loc(chain=chain)
    cand.categories.add(self.cat)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    # base 1.0 + chain same 0.20 + size none 0 = 1.20
    assert match.similarity == round(1.0 + _CHAIN_SAME_BONUS, 2)

  def test_different_chain_gives_smaller_bonus(self):
    chain_a = ChainFactory()
    chain_b = ChainFactory()
    ref = self._loc(chain=chain_a)
    ref.categories.add(self.cat)
    cand = self._loc(chain=chain_b)
    cand.categories.add(self.cat)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(1.0 + _CHAIN_ANY_BONUS, 2)

  def test_same_size_raises_score(self):
    size = SizeFactory(order=2)
    ref = self._loc(size=size)
    ref.categories.add(self.cat)
    cand = self._loc(size=size)
    cand.categories.add(self.cat)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(1.0 + _SIZE_SAME_BONUS, 2)

  def test_adjacent_size_gives_smaller_bonus(self):
    size_a = SizeFactory(order=2)
    size_b = SizeFactory(order=3)
    ref = self._loc(size=size_a)
    ref.categories.add(self.cat)
    cand = self._loc(size=size_b)
    cand.categories.add(self.cat)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(1.0 + _SIZE_ADJACENT_BONUS, 2)

  def test_recommendation_bonus_applied_when_community_score_positive(self):
    ref = self._loc()
    ref.categories.add(self.cat)
    cand = self._loc()
    cand.categories.add(self.cat)
    # Give cand a positive visit
    VisitsFactory(location=cand, recommendation=1, status='p')
    # Use a queryset with visit state annotated
    from django.contrib.auth.models import AnonymousUser
    qs = (
      Location.objects.filter(status='p')
      .with_visit_state(AnonymousUser())
      .select_related('chain', 'size')
      .prefetch_related('tags', 'categories', 'favorited')
    )
    results = get_similar_locations(ref, min_overlap=0.0, queryset=qs)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(1.0 + _RECOMMENDATION_BONUS, 2)

  def test_no_recommendation_bonus_when_unrated(self):
    ref = self._loc()
    ref.categories.add(self.cat)
    cand = self._loc()
    cand.categories.add(self.cat)
    from django.contrib.auth.models import AnonymousUser
    qs = (
      Location.objects.filter(status='p')
      .with_visit_state(AnonymousUser())
      .select_related('chain', 'size')
      .prefetch_related('tags', 'categories', 'favorited')
    )
    results = get_similar_locations(ref, min_overlap=0.0, queryset=qs)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == 1.0

  def test_favorite_bonus_applied_when_favorited(self):
    ref = self._loc()
    ref.categories.add(self.cat)
    cand = self._loc()
    cand.categories.add(self.cat)
    prefs = UserPreferencesFactory()
    prefs.favorites.add(cand)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(1.0 + _FAVORITE_BONUS, 2)

  def test_no_favorite_bonus_when_not_favorited(self):
    ref = self._loc()
    ref.categories.add(self.cat)
    cand = self._loc()
    cand.categories.add(self.cat)
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == 1.0


@pytest.mark.django_db
class TestSimilarLocationsWeighting:
  def setup_method(self):
    _, _, self.dept = make_region_hierarchy()

  def _loc(self, **kwargs):
    return LocationFactory(geo=self.dept, **kwargs)

  def test_higher_weight_tag_increases_base_score(self):
    # ref has one tag with weight 200; cand shares it → base = 200/200 = 1.0
    # same fraction, but now add a second ref tag with weight 100 not shared
    # ref total = 300; shared = 200 → base = 0.67
    heavy = TagFactory(similarity_weight=200)
    light = TagFactory(similarity_weight=100)
    ref = self._loc()
    ref.tags.add(heavy, light)
    cand = self._loc()
    cand.tags.add(heavy)  # only shares the heavy tag
    results = get_similar_locations(ref, min_overlap=0.0)
    match = next(r for r in results if r.pk == cand.pk)
    assert match.similarity == round(200 / 300, 2)

  def test_low_weight_tag_contributes_less_to_score(self):
    # ref has two tags: heavy (200) and light (50); total = 250
    # cand_a shares only light → base = 50/250 = 0.20
    # cand_b shares only heavy → base = 200/250 = 0.80
    heavy = TagFactory(similarity_weight=200)
    light = TagFactory(similarity_weight=50)
    ref = self._loc()
    ref.tags.add(heavy, light)
    cand_a = self._loc()
    cand_a.tags.add(light)
    cand_b = self._loc()
    cand_b.tags.add(heavy)
    results = get_similar_locations(ref, min_overlap=0.0)
    score_a = next(r for r in results if r.pk == cand_a.pk).similarity
    score_b = next(r for r in results if r.pk == cand_b.pk).similarity
    assert score_b > score_a
    assert score_a == round(50 / 250, 2)
    assert score_b == round(200 / 250, 2)

  def test_high_weight_tag_can_push_below_threshold_candidate_above_it(self):
    # ref has one tag with weight 150; candidate shares it → base = 1.0 regardless
    # but with two ref tags (150+100=250), sharing only heavy (150) gives base=0.6
    # with min_overlap=0.5, it passes; sharing only light (100) gives 0.4, fails
    heavy = TagFactory(similarity_weight=150)
    light = TagFactory(similarity_weight=100)
    ref = self._loc()
    ref.tags.add(heavy, light)
    passes = self._loc()
    passes.tags.add(heavy)
    fails = self._loc()
    fails.tags.add(light)
    results = get_similar_locations(ref, min_overlap=0.5)
    pks = [r.pk for r in results]
    assert passes.pk in pks
    assert fails.pk not in pks

  def test_zero_weight_tag_does_not_contribute(self):
    zero = TagFactory(similarity_weight=0)
    normal = TagFactory(similarity_weight=100)
    ref = self._loc()
    ref.tags.add(zero, normal)
    # cand shares only the zero-weight tag → base = 0/100 = 0.0
    cand = self._loc()
    cand.tags.add(zero)
    results = get_similar_locations(ref, min_overlap=0.01)
    assert cand.pk not in [r.pk for r in results]


@pytest.mark.django_db
class TestSimilarLocationsCountryFilter:
  def test_excludes_locations_in_other_country(self):
    _, _, dept_nl = make_region_hierarchy('Netherlands')
    _, _, dept_fr = make_region_hierarchy('France')
    cat = CategoryFactory()

    ref = LocationFactory(geo=dept_nl)
    ref.categories.add(cat)
    nl_cand = LocationFactory(geo=dept_nl)
    nl_cand.categories.add(cat)
    fr_cand = LocationFactory(geo=dept_fr)
    fr_cand.categories.add(cat)

    results = get_similar_locations(ref, min_overlap=0.0)
    pks = [r.pk for r in results]
    assert nl_cand.pk in pks
    assert fr_cand.pk not in pks

  def test_includes_all_countries_when_setting_disabled(self, settings):
    settings.SIMILAR_SAME_COUNTRY = False
    _, _, dept_nl = make_region_hierarchy('Netherlands')
    _, _, dept_fr = make_region_hierarchy('France')
    cat = CategoryFactory()

    ref = LocationFactory(geo=dept_nl)
    ref.categories.add(cat)
    fr_cand = LocationFactory(geo=dept_fr)
    fr_cand.categories.add(cat)

    results = get_similar_locations(ref, min_overlap=0.0)
    assert fr_cand.pk in [r.pk for r in results]

  def test_no_country_filter_when_location_has_no_geo(self):
    cat = CategoryFactory()
    ref = LocationFactory(geo=None)
    ref.categories.add(cat)
    _, _, dept = make_region_hierarchy()
    cand = LocationFactory(geo=dept)
    cand.categories.add(cat)
    # Should not crash and should include the candidate (no country to filter on)
    results = get_similar_locations(ref, min_overlap=0.0)
    assert cand.pk in [r.pk for r in results]
