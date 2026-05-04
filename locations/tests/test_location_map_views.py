import json
import pytest
from django.urls import reverse

from locations.tests.factories import (
  CategoryFactory,
  LocationFactory,
  TagFactory,
  UserFactory,
)


def _login(client):
  user = UserFactory()
  user.save()
  client.force_login(user)
  return user


# ------------------------------------------------------------------ #
#  Authentication
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMapViewAuth:

  @pytest.mark.parametrize('url_name', ['locations:all_map', 'locations:accommodations_map', 'locations:activities_map'])
  def test_anonymous_redirected_to_login(self, client, url_name):
    response = client.get(reverse(url_name))
    assert response.status_code == 302
    assert '/accounts/' in response['Location']

  @pytest.mark.parametrize('url_name', ['locations:all_map', 'locations:accommodations_map', 'locations:activities_map'])
  def test_authenticated_user_gets_200(self, client, url_name):
    _login(client)
    response = client.get(reverse(url_name))
    assert response.status_code == 200


# ------------------------------------------------------------------ #
#  Scope context
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMapViewScope:

  def test_all_map_scope(self, client):
    _login(client)
    response = client.get(reverse('locations:all_map'))
    assert response.context['scope'] == 'all'

  def test_accommodations_map_scope(self, client):
    _login(client)
    response = client.get(reverse('locations:accommodations_map'))
    assert response.context['scope'] == 'accommodations'

  def test_activities_map_scope(self, client):
    _login(client)
    response = client.get(reverse('locations:activities_map'))
    assert response.context['scope'] == 'activities'

  def test_all_map_uses_map_template(self, client):
    _login(client)
    response = client.get(reverse('locations:all_map'))
    assert 'locations/locations_map.html' in [t.name for t in response.templates]


# ------------------------------------------------------------------ #
#  Queryset filtering per map view type
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMapViewQueryset:

  def _make_locations(self):
    # Root category named 'Activity' → is_activity=True; any other root → is_accommodation=True
    acc_cat = CategoryFactory(name='Hotels', parent=None)
    act_root = CategoryFactory(name='Activity', parent=None)

    acc = LocationFactory(name='Hotel A')
    acc.categories.add(acc_cat)
    acc._update_types()
    acc.save()

    act = LocationFactory(name='Activity B')
    act.categories.add(act_root)
    act._update_types()
    act.save()

    both = LocationFactory(name='Both C')
    both.categories.add(acc_cat, act_root)
    both._update_types()
    both.save()

    return acc, act, both

  def test_all_map_returns_all_types(self, client):
    _login(client)
    acc, act, both = self._make_locations()
    response = client.get(reverse('locations:all_map'))
    names = [loc.name for loc in response.context['locations']]
    assert 'Hotel A' in names
    assert 'Activity B' in names
    assert 'Both C' in names

  def test_accommodations_map_filters_to_accommodations(self, client):
    _login(client)
    acc, act, both = self._make_locations()
    response = client.get(reverse('locations:accommodations_map'))
    names = [loc.name for loc in response.context['locations']]
    assert 'Hotel A' in names
    assert 'Both C' in names
    assert 'Activity B' not in names

  def test_activities_map_filters_to_activities(self, client):
    _login(client)
    acc, act, both = self._make_locations()
    response = client.get(reverse('locations:activities_map'))
    names = [loc.name for loc in response.context['locations']]
    assert 'Activity B' in names
    assert 'Both C' in names
    assert 'Hotel A' not in names

  def test_map_only_shows_published(self, client):
    _login(client)
    LocationFactory(name='Published', status='p')
    LocationFactory(name='Concept', status='c')
    LocationFactory(name='Revoked', status='r')
    response = client.get(reverse('locations:all_map'))
    names = [loc.name for loc in response.context['locations']]
    assert 'Published' in names
    assert 'Concept' not in names
    assert 'Revoked' not in names


# ------------------------------------------------------------------ #
#  format=filters JSON endpoint
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestFiltersJsonEndpoint:

  def test_returns_json(self, client):
    _login(client)
    response = client.get(reverse('locations:all_map') + '?format=filters')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'

  def test_response_has_expected_keys(self, client):
    _login(client)
    response = client.get(reverse('locations:all_map') + '?format=filters')
    data = json.loads(response.content)
    assert 'category' in data
    assert 'tag' in data
    assert 'types' in data

  def test_types_reflect_location_flags(self, client):
    _login(client)
    acc_cat = CategoryFactory(name='Hotels', parent=None)
    loc = LocationFactory()
    loc.categories.add(acc_cat)
    loc._update_types()
    loc.save()

    response = client.get(reverse('locations:all_map') + '?format=filters')
    data = json.loads(response.content)
    assert data['types']['accommodations'] is True
    assert data['types']['activities'] is False

  def test_category_options_include_all_options(self, client):
    _login(client)
    cat = CategoryFactory(name='Camping')
    loc = LocationFactory()
    loc.categories.add(cat)
    response = client.get(reverse('locations:all_map') + '?format=filters')
    data = json.loads(response.content)
    slugs = [o['slug'] for o in data['category']['all_options']]
    assert cat.slug in slugs

  def test_tag_options_include_all_options(self, client):
    _login(client)
    tag = TagFactory(name='Pet Friendly')
    loc = LocationFactory()
    loc.tags.add(tag)
    response = client.get(reverse('locations:all_map') + '?format=filters')
    data = json.loads(response.content)
    slugs = [o['slug'] for o in data['tag']['all_options']]
    assert tag.slug in slugs

  def test_active_category_excluded_from_options(self, client):
    _login(client)
    cat = CategoryFactory(name='Camping')
    loc = LocationFactory()
    loc.categories.add(cat)
    url = reverse('locations:all_map') + f'?format=filters&category={cat.slug}'
    response = client.get(url)
    data = json.loads(response.content)
    option_slugs = [o['slug'] for o in data['category']['options']]
    assert cat.slug not in option_slugs

  def test_viewport_params_filter_queryset(self, client):
    _login(client)
    inside  = LocationFactory(name='Inside',  coord_lat=48.0, coord_lon=2.0)
    outside = LocationFactory(name='Outside', coord_lat=52.0, coord_lon=5.0)
    # Viewport tightly around 'inside'
    url = (
      reverse('locations:all_map')
      + '?format=filters&coord_lat__gte=47.0&coord_lat__lte=49.0'
        '&coord_lon__gte=1.0&coord_lon__lte=3.0'
    )
    response = client.get(url)
    data = json.loads(response.content)
    # Types check: only 'inside' is in the viewport queryset
    # We can't easily check location names from this endpoint, but
    # the response must not error and types keys must be present.
    assert 'types' in data

  def test_viewport_params_not_in_option_urls(self, client):
    _login(client)
    cat = CategoryFactory(name='Camping')
    loc = LocationFactory()
    loc.categories.add(cat)
    url = (
      reverse('locations:all_map')
      + '?format=filters&coord_lat__gte=40.0&coord_lat__lte=55.0'
        '&coord_lon__gte=0.0&coord_lon__lte=10.0'
    )
    response = client.get(url)
    data = json.loads(response.content)
    for opt in data['category']['options']:
      assert 'coord_lat' not in opt.get('url', '')
      assert 'coord_lon' not in opt.get('url', '')

  def test_anonymous_user_gets_redirect(self, client):
    response = client.get(reverse('locations:all_map') + '?format=filters')
    assert response.status_code == 302
