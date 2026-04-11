import pytest
from django.urls import reverse
from locations.tests.factories import (
    LocationFactory,
    RegionFactory,
    CategoryFactory,
    TagFactory,
    ChainFactory,
    UserFactory,
)


# ------------------------------------------------------------------ #
#  Basic View Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationListView:
    
    def test_location_list_view_exists(self, client):
        """View is accessible at correct URL."""
        url = reverse('locations:home')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_location_list_uses_correct_template(self, client):
        """View uses the location list template."""
        url = reverse('locations:home')
        response = client.get(url)
        assert 'locations/locations_list.html' in [t.name for t in response.templates]
    
    def test_location_list_only_shows_published(self, client):
        """Only published locations appear in the list."""
        published = LocationFactory(name='Published Location', status='p')
        concept = LocationFactory(name='Concept Location', status='c')
        revoked = LocationFactory(name='Revoked Location', status='r')
        deleted = LocationFactory(name='Deleted Location', status='x')
        
        url = reverse('locations:home')
        response = client.get(url)
        
        # Test the queryset in context, not HTML content
        locations = response.context['locations']
        location_names = [loc.name for loc in locations]
        
        assert 'Published Location' in location_names
        assert 'Concept Location' not in location_names
        assert 'Revoked Location' not in location_names
        assert 'Deleted Location' not in location_names
    
    def test_location_list_empty_state(self, client):
        """Empty list shows appropriate message."""
        url = reverse('locations:home')
        response = client.get(url)
        assert response.status_code == 200
        # Check context or content for empty state


# ------------------------------------------------------------------ #
#  Filtering Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationListFiltering:
    
    def test_filter_by_region(self, client):
        """Filtering by region shows only locations in that region."""
        # Create proper hierarchy: country → region → department
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        utrecht_region = RegionFactory(name='Utrecht', parent=netherlands, level='region')
        utrecht_dept = RegionFactory(name='Utrecht City', parent=utrecht_region, level='department')
        
        belgium = RegionFactory(name='Belgium', parent=None, level='country')
        brussels_region = RegionFactory(name='Brussels', parent=belgium, level='region')
        brussels_dept = RegionFactory(name='Brussels City', parent=brussels_region, level='department')
        
        # Locations at department level (3 levels deep)
        nl_location = LocationFactory(name='Amsterdam Hotel', geo=utrecht_dept)
        be_location = LocationFactory(name='Brussels Hotel', geo=brussels_dept)
        
        # Filter by country slug (3 levels up from location.region)
        url = reverse('locations:home') + f'?country={netherlands.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Amsterdam Hotel' in content
        assert 'Brussels Hotel' not in content

    def test_filter_by_country(self, client):
        """Filtering by country (region level) works."""
        # Create hierarchy
        france = RegionFactory(name='France', parent=None, level='country')
        ile_de_france = RegionFactory(name='Île-de-France', parent=france, level='region')
        paris_dept = RegionFactory(name='Paris', parent=ile_de_france, level='department')
        
        # Location at department level
        paris_location = LocationFactory(name='Paris Hotel', geo=paris_dept)
        other_location = LocationFactory(name='Other Hotel', geo=None)
        
        url = reverse('locations:home') + f'?country={france.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Paris Hotel' in content
        assert 'Other Hotel' not in content
    
    def test_filter_by_accommodation_type(self, client):
        """Filter shows only accommodations."""
        hotel_cat = CategoryFactory(name='Hotels', parent=None)
        activity_cat = CategoryFactory(name='Activity', parent=None)
        
        hotel = LocationFactory(name='Nice Hotel')
        hotel.categories.add(hotel_cat)
        hotel._update_types()
        hotel.save()
        
        museum = LocationFactory(name='Museum')
        museum.categories.add(activity_cat)
        museum._update_types()
        museum.save()
        
        url = reverse('locations:home') + '?is_accommodation=true'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Nice Hotel' in content
        assert 'Museum' not in content
    
    def test_filter_by_activity_type(self, client):
        """Filter shows only activities."""
        hotel_cat = CategoryFactory(name='Hotels', parent=None)
        activity_cat = CategoryFactory(name='Activity', parent=None)
        
        hotel = LocationFactory(name='Nice Hotel')
        hotel.categories.add(hotel_cat)
        hotel._update_types()
        hotel.save()
        
        museum = LocationFactory(name='Museum')
        museum.categories.add(activity_cat)
        museum._update_types()
        museum.save()
        
        url = reverse('locations:home') + '?is_activity=true'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Museum' in content
        assert 'Nice Hotel' not in content
    
    def test_filter_by_category(self, client):
        """Filter by specific category."""
        camping_cat = CategoryFactory(name='Camping')
        hotel_cat = CategoryFactory(name='Hotel')
        
        camping = LocationFactory(name='Nice Camping')
        camping.categories.add(camping_cat)
        
        hotel = LocationFactory(name='Nice Hotel')
        hotel.categories.add(hotel_cat)
        
        url = reverse('locations:home') + f'?category={camping_cat.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Nice Camping' in content
        assert 'Nice Hotel' not in content
    
    def test_filter_by_tag(self, client):
        """Filter by tag."""
        pet_friendly = TagFactory(name='Pet Friendly')
        family_friendly = TagFactory(name='Family Friendly')
        
        pet_location = LocationFactory(name='Pet Hotel')
        pet_location.tags.add(pet_friendly)
        
        family_location = LocationFactory(name='Family Resort')
        family_location.tags.add(family_friendly)
        
        url = reverse('locations:home') + f'?tag={pet_friendly.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Pet Hotel' in content
        assert 'Family Resort' not in content
    
    def test_filter_by_chain(self, client):
        """Filter by chain."""
        novotel = ChainFactory(name='Novotel')
        marriott = ChainFactory(name='Marriott')
        
        novotel_hotel = LocationFactory(name='Novotel Amsterdam', chain=novotel)
        marriott_hotel = LocationFactory(name='Marriott Brussels', chain=marriott)
        
        url = reverse('locations:home') + f'?chain__slug={novotel.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Novotel Amsterdam' in content
        assert 'Marriott Brussels' not in content
    
    def test_multiple_filters_combined(self, client):
        """Multiple filters work together (AND logic)."""
        # Create proper 3-level hierarchy
        netherlands = RegionFactory(name='Netherlands', parent=None, level='country')
        noord_holland = RegionFactory(name='Noord-Holland', parent=netherlands, level='region')
        amsterdam = RegionFactory(name='Amsterdam', parent=noord_holland, level='department')
        
        belgium = RegionFactory(name='Belgium', parent=None, level='country')
        vlaanderen = RegionFactory(name='Vlaanderen', parent=belgium, level='region')
        antwerpen = RegionFactory(name='Antwerpen', parent=vlaanderen, level='department')
        
        camping_cat = CategoryFactory(name='Camping')
        hotel_cat = CategoryFactory(name='Hotel')
        pet_tag = TagFactory(name='Pet Friendly')
        family_tag = TagFactory(name='Family Friendly')
        
        # Matches all criteria (country + category + tag)
        matching = LocationFactory(name='Pet Camping NL', geo=amsterdam)
        matching.categories.add(camping_cat)
        matching.tags.add(pet_tag)
        matching._update_types()
        matching.save()
        
        # Wrong country (Belgium instead of Netherlands)
        wrong_country = LocationFactory(name='Pet Camping BE', geo=antwerpen)
        wrong_country.categories.add(camping_cat)
        wrong_country.tags.add(pet_tag)
        wrong_country._update_types()
        wrong_country.save()
        
        # Wrong category (Hotel instead of Camping)
        wrong_category = LocationFactory(name='Pet Hotel NL', geo=amsterdam)
        wrong_category.categories.add(hotel_cat)
        wrong_category.tags.add(pet_tag)
        wrong_category._update_types()
        wrong_category.save()
        
        # Wrong tag (Family instead of Pet)
        wrong_tag = LocationFactory(name='Family Camping NL', geo=amsterdam)
        wrong_tag.categories.add(camping_cat)
        wrong_tag.tags.add(family_tag)
        wrong_tag._update_types()
        wrong_tag.save()
        
        # Use slug-based filters via mapping
        url = reverse('locations:home') + f'?country={netherlands.slug}&category={camping_cat.slug}&tag={pet_tag.slug}'
        response = client.get(url)
        content = response.content.decode()
        
        # Only the location matching ALL criteria should appear
        assert 'Pet Camping NL' in content
        assert 'Pet Camping BE' not in content
        assert 'Pet Hotel NL' not in content
        assert 'Family Camping NL' not in content


# ------------------------------------------------------------------ #
#  Search Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationListSearch:
    
    def test_search_by_name(self, client):
        """Search finds locations by name."""
        LocationFactory(name='Amsterdam Paradise Hotel')
        LocationFactory(name='Brussels Grand Hotel')
        
        url = reverse('locations:home') + '?name=amsterdam'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Amsterdam Paradise' in content
        assert 'Brussels Grand' not in content
    
    def test_search_case_insensitive(self, client):
        """Search is case insensitive."""
        LocationFactory(name='Amsterdam Hotel')
        
        url = reverse('locations:home') + '?name=AMSTERDAM'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Amsterdam Hotel' in content
    
    def test_search_by_address(self, client):
        """Search finds locations by address."""
        LocationFactory(name='Hotel Central', address='Damrak 1, Amsterdam')
        LocationFactory(name='Hotel West', address='Main Street, Brussels')
        
        url = reverse('locations:home') + '?address=damrak'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Hotel Central' in content
        assert 'Hotel West' not in content
    
    def test_search_partial_match(self, client):
        """Search works with partial matches."""
        LocationFactory(name='Camping Paradise')
        
        url = reverse('locations:home') + '?name=para'
        response = client.get(url)
        content = response.content.decode()
        
        assert 'Camping Paradise' in content
    
    def test_search_no_results(self, client):
        """Search with no matches shows empty state."""
        LocationFactory(name='Hotel Amsterdam')
        
        url = reverse('locations:home') + '?name=nonexistent'
        response = client.get(url)
        
        assert response.status_code == 200
        # Should show "no results" message


# ------------------------------------------------------------------ #
#  Context Data Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationListContext:
    
    def test_context_includes_locations(self, client):
        """Context includes locations queryset."""
        LocationFactory(name='Test Location')
        
        url = reverse('locations:home')
        response = client.get(url)
        
        assert 'locations' in response.context
        assert response.context['locations'].count() == 1
    
    def test_context_includes_filter_options(self, client):
        """Context includes available filter options."""
        url = reverse('locations:home')
        response = client.get(url)

        assert 'region_filter_options' in response.context
    
    def test_context_includes_active_filters(self, client):
        """Context shows which filters are currently active."""
        region = RegionFactory(name='Netherlands')
        
        url = reverse('locations:home') + f'?region={region.id}'
        response = client.get(url)
        
        # Should track active filters for UI
        assert 'active_filters' in response.context


# ------------------------------------------------------------------ #
#  Ordering Tests
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestLocationListOrdering:
    
    def test_default_ordering_by_name(self, client):
        """Locations are ordered by name by default."""
        LocationFactory(name='Zebra Hotel')
        LocationFactory(name='Alpha Hotel')
        LocationFactory(name='Beta Hotel')
        
        url = reverse('locations:home')
        response = client.get(url)
        
        names = [loc.name for loc in response.context['locations']]
        assert names == sorted(names)
    
    def test_ordering_by_parameter(self, client):
        """Can order by different fields via query param."""
        LocationFactory(name='New Hotel', date_created='2024-01-01')
        LocationFactory(name='Old Hotel', date_created='2023-01-01')
        
        url = reverse('locations:home') + '?order_by=-date_created'
        response = client.get(url)
        
        names = [loc.name for loc in response.context['locations']]
        assert names[0] == 'New Hotel'


# ------------------------------------------------------------------ #
#  Authentication banner
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestAuthBanner:

  def test_banner_shown_to_anonymous_user(self, client):
    url = reverse('locations:home')
    response = client.get(url)
    assert b'Create an account' in response.content

  def test_banner_not_shown_to_authenticated_user(self, client):
    user = UserFactory()
    user.save()
    client.force_login(user)
    url = reverse('locations:home')
    response = client.get(url)
    assert b'Create an account' not in response.content