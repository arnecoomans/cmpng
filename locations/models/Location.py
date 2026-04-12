from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from django.urls import reverse_lazy
from django.utils.text import slugify, capfirst
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib import messages
from django.db.models import FloatField, IntegerField, Value, Prefetch, F
from django.db.models.functions import Coalesce

# from traceback import format_exc

from cmnsd.models import BaseModel, VisibilityModel
from cmnsd.models.BaseMethods import ajax_function, searchable_function

from .mixins import LocationAccessMixin
from .Region import Region
from .Category import Category
from .Tag import Tag
from .Chain import Chain
from .Comment import Comment

from locations.utils import get_departure_coordinates

# ================================================================
# Supportive models: Size
# ================================================================

# ================================================================
# Main Location Model with Custom Manager and QuerySet
# - The Location model itself is defined at the end, after the QuerySet 
#   and Manager for better readability.
# - The QuerySet contains chainable methods for optimizations, 
#   and the Manager provides convenience methods to access those 
#   optimizations directly from the model.
# ================================================================
''' Location Queryset '''
class LocationQuerySet(models.QuerySet):
  """Custom queryset with chainable optimizations."""
    
  def with_relations(self):
    """Add select_related and prefetch_related."""
    return self.select_related(
      'geo',
      'geo__parent',
      'geo__parent__parent',
      'chain',
      'chain__parent',
      'size',
    ).prefetch_related(
      Prefetch('categories', queryset=Category.objects.order_by(F('parent__name').asc(nulls_first=True), 'name')),
      Prefetch('tags', queryset=Tag.objects.order_by(F('parent__name').asc(nulls_first=True), 'name')),
      'visitors',
      'home_of',
      'favorited',
      'media',
    )
  
  def with_distances(self):
    """Add distance annotations."""
    return self.annotate(
      country_distance=Coalesce(
        'geo__parent__parent__cached_average_distance_to_center', 
        Value(999999.0), 
        output_field=FloatField()
      ),
      region_distance=Coalesce(
        'geo__parent__cached_average_distance_to_center', 
        Value(999999.0), 
        output_field=FloatField()
      ),
      department_distance=Coalesce(
        'geo__cached_average_distance_to_center', 
        Value(999999.0), 
        output_field=FloatField()
      ),
      location_distance=Coalesce(
        'distance_to_departure_center', 
        Value(999999), 
        output_field=IntegerField()
      ),
    )
    
  def with_default_ordering(self):
    """Apply default hierarchical ordering."""
    return self.order_by(
      'country_distance',
      'geo__parent__parent__name',
      'region_distance',
      'geo__parent__name',
      'department_distance',
      'geo__name',
      'location_distance',
      'name'
    )
  
  def with_comments(self):
    """Prefetch published comments."""
    from locations.models.Comment import Comment
    return self.prefetch_related(
      Prefetch(
        'comments',
        queryset=Comment.objects.filter(status='p').order_by('-date_created'),
        to_attr='prefetched_comments',
      ),
    )

  def with_visit_state(self, user):
    """Annotate each location with visit state data for the given user.

    Adds four annotations:
      visit_anyone_visited (bool): True if any user has visited this location.
      visit_user_visited (bool): True if the given user has visited.
      visit_user_recommendation (int|None): user's most recent recommendation value.
      visit_community_score (float|None): average recommendation across all rated visits.

    Use visit_state_from_annotation() from visits_recommendation service to
    convert these to a state string.
    """
    from django.db.models import Subquery, OuterRef, Exists, IntegerField, FloatField, Value, Avg
    from django.db.models.expressions import RawSQL
    from locations.models.Visits import Visits

    anyone_visited = Visits.objects.filter(location=OuterRef('pk'), status='p')

    # Two-level avg: per-user first, then community — gives each user one vote
    community_score = RawSQL(
      '(SELECT AVG(u_avg) FROM ('
      '  SELECT AVG(recommendation) AS u_avg'
      '  FROM locations_visits'
      '  WHERE location_id = "locations_location"."id"'
      '    AND recommendation IS NOT NULL'
      '    AND status = \'p\''
      '  GROUP BY user_id'
      ') t)',
      [],
      output_field=FloatField(),
    )

    if getattr(user, 'is_authenticated', False):
      user_visits = Visits.objects.filter(location=OuterRef('pk'), user=user, status='p')
      user_recommendation = Subquery(
        user_visits.order_by('-year', '-month', '-day').values('recommendation')[:1],
        output_field=IntegerField(),
      )
      user_visited = Exists(user_visits)
    else:
      user_recommendation = Value(None, output_field=IntegerField())
      user_visited = Value(False)

    return self.annotate(
      visit_anyone_visited=Exists(anyone_visited),
      visit_user_visited=user_visited,
      visit_user_recommendation=user_recommendation,
      visit_community_score=community_score,
    )

  def optimized(self):
    """Full optimization - everything in one call."""
    return self.with_relations().with_distances().with_default_ordering().with_comments()

''' Location Manager '''
class LocationManager(models.Manager):
  """Custom manager."""
    
  def get_queryset(self):
    return LocationQuerySet(self.model, using=self._db)
    
  # Proxy methods for convenience
  def with_relations(self):
    return self.get_queryset().with_relations()
  
  def with_distances(self):
    return self.get_queryset().with_distances()
  
  def with_visit_state(self, user):
    return self.get_queryset().with_visit_state(user)

  def optimized(self):
    return self.get_queryset().optimized()
    
''' Location Model '''
class Location(LocationAccessMixin, BaseModel, VisibilityModel):
  # Slug is used for URL and should be unique
  slug = models.SlugField(max_length=255, unique=True)
  # Directly stored information fields
  name = models.CharField(max_length=255)
  summary = models.CharField(max_length=500, blank=True, null=True)
  description = models.TextField(blank=True, default='', help_text=_('Markdown is supported'))
  address = models.CharField(max_length=255, blank=True, null=True)
  email = models.EmailField(blank=True, null=True)
  phone = models.CharField(max_length=50, blank=True, null=True)
  owners_name = models.CharField(max_length=255, blank=True, null=True)
  coord_lat = models.FloatField(blank=True, null=True)
  coord_lon = models.FloatField(blank=True, null=True)
  google_place_id = models.CharField(max_length=255, blank=True, null=True)
  # Type Flags - are set in save() and derived from category, but stored here for easier querying
  is_accommodation = models.BooleanField(default=True, editable=False)
  is_activity = models.BooleanField(default=False, editable=False)
  # Relations
  geo = models.ForeignKey('Region',null=True, blank=True, on_delete=models.SET_NULL, related_name='locations')
  categories = models.ManyToManyField('Category', related_name='locations', blank=True)
  tags = models.ManyToManyField('Tag', related_name='locations', blank=True)
  chain = models.ForeignKey('Chain', null=True, blank=True, on_delete=models.SET_NULL, related_name='locations')
  # ================================================================
  # Profile related fields
  # ================================================================
  # Visitor is defined in Preferences.Visitors, but we also want a direct M2M here
  # to add visitor Users to the Location model for easier querying and display. 
  # This is a "through" relation to the Visits model.
  visitors = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    through='Visits',
    related_name='visited_locations',
    blank=True,
  )
  # Comments are defined in the Comments model, but we can also have a reverse relation here for easier access.
  comments = GenericRelation(Comment)
  # Implied relation: links in Link model
  # Implied relation lists in List model (through M2M with Location)
  size = models.ForeignKey(
    'Size',
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name='locations'
  )
  # ================================================================
  #  Caching Fields 
  # ================================================================
  # Distance caching
  distance_to_departure_center = models.IntegerField(
    null=True,
    blank=True,
    help_text=capfirst(_('distance in km from departure center'))
  )
  # Completeness score (0-100), recalculated via signals
  completeness = models.IntegerField(default=0, editable=False)

  # Use custom manager
  objects = LocationManager()

  # Meta
  class Meta:
    ordering = ['name']
    indexes = [
      models.Index(fields=['status', 'visibility'], name='location_status_visibility_idx'),
      models.Index(fields=['is_accommodation'], name='location_is_accommodation_idx'),
      models.Index(fields=['is_activity'], name='location_is_activity_idx'),
    ]

  # Methods
  def __str__(self):
    return self.name

  def get_absolute_url(self):
    """ Return the canonical URL for this location based on its type. """
    if self.is_accommodation:
      # Even if a location is both accommodation and activity, 
      # accommodation takes precedence for URL structure
      return reverse_lazy('locations:accommodation_detail', kwargs={'slug': self.slug})
    elif self.is_activity:
      return reverse_lazy('locations:activity_detail', kwargs={'slug': self.slug})
    else:
      # Fall back to a generic location detail if undetermined
      return reverse_lazy('locations:location_detail', kwargs={'slug': self.slug})
  
  def get_type_list_url(self):
    if self.is_accommodation:
      return reverse_lazy('locations:accommodations') 
    elif self.is_activity:
      return reverse_lazy('locations:activities')
    else:
      return reverse_lazy('locations:all')
  
  # ================================================================
  # Save Function and Save Routines
  # - This is where we handle slug generation and type detection based on categories.
  # - We also have a method to calculate distance to departure center, 
  #   which can be called from views or management commands to update distances when needed.
  # ================================================================
  def save(self, *args, **kwargs):
    """ Generate slug from name if not provided """
    if not self.slug:
      self.slug = slugify(self.name)
    super().save(*args, **kwargs)
    """ Update types after save (since we need M2M to exist) """
    if self.pk:
      self._update_types()
      """ Save again with updated flags """
      super(Location, self).save(update_fields=['is_accommodation', 'is_activity'])
    """ Fetch place_id from Google if missing (full save only, API key required) """
    update_fields = kwargs.get('update_fields')
    if (
      self.pk
      and not self.google_place_id
      and update_fields is None
      and getattr(settings, 'GOOGLE_API_KEY', None)
    ):
      from django.db import transaction
      try:
        with transaction.atomic():
          from locations.services.location_geocoding import fetch_place_id
          fetch_place_id(self)
      except Exception:
        pass

  # Internal method to detect and set type flags based on categories. Called in save() after M2M is set.
  def _update_types(self):
    """ Recalculate type flags from categories. """
    if not self.categories.exists():
      # No categories — preserve any seeded values (e.g. from Google types).
      # Only apply the default when neither flag has been explicitly set.
      if not self.is_accommodation and not self.is_activity:
        self.is_accommodation = True
      return
    # Categories present — derive entirely from them.
    self.is_accommodation = False
    self.is_activity = False
    for category in self.categories.all():
      """ Walk through category hierarchy and detect if one of the root categories is "Activity" """
      root = category
      while root.parent:
        root = root.parent
      if root.name == 'Activity':
        self.is_activity = True
      else:
        self.is_accommodation = True

  # Type property that uses the boolean flags to return a string type for easier template use
  @property
  def type(self):
    if self.is_activity and not self.is_accommodation:
      return _('activity')
    elif self.is_accommodation and not self.is_activity:
      return _('accommodation')
    else:
      return _('mixed')
    
  @property
  def favorited_by(self):
    if not hasattr(self, '_favorited_by'):
      """ Return users who have favorited this location. 
          This is a convenience property that accesses the M2M through Preferences.
      """
      from django.contrib.auth import get_user_model
      self._favorited_by = get_user_model().objects.filter(preferences__favorites=self)
    return self._favorited_by
  
  @searchable_function
  def is_visited(self):
    if not hasattr(self, '_is_visited'):
      if hasattr(self, 'request') and self.request.user.is_authenticated:
        self._is_visited = self.visitors.filter(pk=self.request.user.pk).exists()
      else:
        self._is_visited = False
    return self._is_visited

  @searchable_function
  def is_favorite(self):
    if not hasattr(self, '_is_favorite'):
      if hasattr(self, 'request') and self.request.user.is_authenticated:
        self._is_favorite = self.favorited_by.filter(pk=self.request.user.pk).exists()
      else:
        self._is_favorite = False
    return self._is_favorite
  
  def can_have_size(self):
    """Return True if any Size exists for any of this location's categories."""
    from locations.models.Size import Size
    return Size.objects.filter(categories__in=self.categories.all()).exists()

  def calculate_completeness(self):
    """Compute and store the completeness score (0–100).

    Points are normalised against the applicable maximum so conditional
    criteria (e.g. size) do not penalise locations that can never earn them.
    Bonus points for visits and list appearances are added after normalisation,
    capped at 100.
    """
    # Scoring weights — applicable_max is the sum of all weights below
    # (categories and tags are tiered; max values used for applicable_max)
    SCORES = {
      'address':      10,  # auto-filled, lower credit
      'summary':      20,  # primary text — most important
      'link':         20,  # important external reference
      'category_1':  10,  # at least one category
      'category_2':   5,  # two or more (slightly better)
      'description':  10,  # longer-form, edit-only
      'media':        10,  # public/community photo
      'tag_1':         5,  # at least one tag
      'tag_2':         5,  # two or more tags
    }
    # Bonuses applied after normalisation, capped at 100.
    # These reward active use and conditional enrichment without affecting the base max.
    BONUSES = {
      'visited':  10,  # location has been visited — signals real-world value
      'on_list':  10,  # location appears on a trip list — signals planning value
      'comments':  5,  # has community comments — signals engagement
      'size':      5,  # size set when applicable — conditional enrichment
    }

    applicable_max = sum(SCORES.values())  # 95

    category_count = self.categories.count()
    tag_count = self.tags.count()
    has_media = self.media.filter(visibility__in=('p', 'c'), status='p').exists()

    earned = 0
    if self.address:
      earned += SCORES['address']
    if self.summary:
      earned += SCORES['summary']
    if self.links.exists():
      earned += SCORES['link']
    if category_count >= 1:
      earned += SCORES['category_1']
    if category_count >= 2:
      earned += SCORES['category_2']
    if self.description:
      earned += SCORES['description']
    if has_media:
      earned += SCORES['media']
    if tag_count >= 1:
      earned += SCORES['tag_1']
    if tag_count >= 2:
      earned += SCORES['tag_2']

    score = round((earned / applicable_max) * 100) if applicable_max else 0

    if self.visitors.exists():
      score = min(100, score + BONUSES['visited'])
    if self.list_items.exists():
      score = min(100, score + BONUSES['on_list'])
    if self.comments.filter(status='p').exists():
      score = min(100, score + BONUSES['comments'])
    if self.can_have_size() and self.size:
      score = min(100, score + BONUSES['size'])

    Location.objects.filter(pk=self.pk).update(completeness=score)
    self.completeness = score

  def completeness_hints(self):
    """Return criteria and deductions as (label, status) tuples.

    Status is one of: 'done', 'missing', 'deduction'.
    """
    category_count = self.categories.count()
    tag_count = self.tags.count()
    has_media = self.media.filter(visibility__in=('p', 'c'), status='p').exists()
    hints = [
      (_('address'),              'done' if self.address else 'missing'),
      (_('summary'),              'done' if self.summary else 'missing'),
      (_('link'),                 'done' if self.links.exists() else 'missing'),
      (_('category'),             'done' if category_count >= 1 else 'missing'),
      (_('multiple categories'),  'done' if category_count >= 2 else 'missing'),
      (_('description'),          'done' if self.description else 'missing'),
      (_('media'),                'done' if has_media else 'missing'),
      (_('tag'),                  'done' if tag_count >= 1 else 'missing'),
      (_('multiple tags'),        'done' if tag_count >= 2 else 'missing'),
    ]
    hints.append((_('visited (+10%)'),    'bonus' if self.visitors.exists() else 'missing'))
    hints.append((_('on a list (+10%)'),  'bonus' if self.list_items.exists() else 'missing'))
    hints.append((_('comments (+5%)'),    'bonus' if self.comments.filter(status='p').exists() else 'missing'))
    if self.can_have_size():
      hints.append((_('size (+5%)'), 'bonus' if self.size else 'missing'))
    return hints

  def available_sizes(self):
    """Return all unique sizes available for this location's categories."""
    from locations.models.Size import Size
    return Size.objects.filter(categories__in=self.categories.all()).distinct()
  
  # ================================================================
  # Simple Classmethods (data access, no external dependencies)
  # ================================================================
  @classmethod
  def get_optimized_queryset(cls):
    """
    Return an optimized queryset with relations, annotations, and ordering.
    Use this in views, AJAX calls, management commands, etc.
    """
    return cls.objects.optimized()
  
  @classmethod
  def get_filter_mapping(cls):
      """
      Return a mapping of URL parameter aliases to actual field lookups.
      
      This allows cleaner URLs:
        ?country=nl          → geo__parent__parent__slug=nl
        ?region=utrecht → geo__parent__slug=utrecht
        ?tag=pet-friendly    → tags__slug=pet-friendly
      """
      return {
          'country': 'geo__parent__parent__slug',
          'region': 'geo__parent__slug',
          'department': 'geo__slug',
          'category': 'categories__slug',
          'tag': 'tags__slug',
      }
  
  # ================================================================
  # Delegation to Services: Query Services
  # ================================================================

  @classmethod
  def get_categories_from_queryset(cls, queryset, limit=20, min_usage=1):
      """Get unique categories from a location queryset. Delegates to service."""
      from locations.services.location_queries import get_categories_from_queryset
      return get_categories_from_queryset(queryset, limit=limit, min_usage=min_usage)

  @classmethod
  def get_tags_from_queryset(cls, queryset, limit=20, min_usage=1):
      """Get unique tags from a location queryset. Delegates to service."""
      from locations.services.location_queries import get_tags_from_queryset
      return get_tags_from_queryset(queryset, limit=limit, min_usage=min_usage)

  @classmethod
  def get_countries_with_locations(cls, queryset=None):
      """Get all countries that have locations. Delegates to service."""
      from locations.services.location_queries import get_countries_with_locations
      return get_countries_with_locations(queryset)

  @classmethod
  def get_regions_with_locations(cls, queryset=None):
      """Get all regions that have locations. Delegates to service."""
      from locations.services.location_queries import get_regions_with_locations
      return get_regions_with_locations(queryset)

  @classmethod
  def get_departments_with_locations(cls, queryset=None):
      """Get all departments that have locations. Delegates to service."""
      from locations.services.location_queries import get_departments_with_locations
      return get_departments_with_locations(queryset)
  
  # ================================================================
  # Service Delegation: Geocoding and Distance Calculation
  # - These methods can be called from views, management commands, or even signals 
  #   to geocode addresses and calculate distances when needed.
  # ================================================================
  
  def fetch_address(self, request=None):
    """Fetch address from Google by name if missing. Delegates to service."""
    from locations.services.location_geocoding import fetch_address
    return fetch_address(self, request=request)

  def geocode(self, request=None):
    """Geocode address → coordinates. Delegates to service."""
    from locations.services.location_geocoding import geocode_location
    return geocode_location(self, request=request)

  def enrich(self, request=None):
    """Full enrichment pipeline: address → coordinates → geo. Delegates to service."""
    from locations.services.location_geocoding import enrich_location
    return enrich_location(self, request=request)

  def fetch_place_id(self):
    """Fetch and store Google place_id if missing. Delegates to service."""
    from locations.services.location_geocoding import fetch_place_id
    return fetch_place_id(self)

  def fetch_phone(self):
    """Fetch and store phone from Google Places Details if blank. Delegates to service."""
    from locations.services.location_geocoding import fetch_phone
    return fetch_phone(self)
  
  def calculate_distance_to_departure_center(self, request=None):
    """Calculate distance to departure center. Delegates to service."""
    from locations.services.location_distance import calculate_distance_to_departure_center
    return calculate_distance_to_departure_center(self, request=request)
  
  @ajax_function
  def nearby(self, radius_km=None, queryset=None):
    from locations.services.location_nearby import get_nearby_locations
    MAX_RANGE = 500

    if hasattr(self, 'request') and not self.request.user.is_authenticated:
      # Guests always use the fixed guest range — no override allowed
      radius_km = getattr(settings, 'GUEST_NEARBY_RANGE', 35)
    elif hasattr(self, 'request') and self.request.user.is_authenticated:
      # Authenticated users may request a custom range via ?radius_km=X
      try:
        requested = float(self.request.GET.get('radius_km', 0))
        radius_km = min(requested, MAX_RANGE) if requested > 0 else (radius_km or getattr(settings, 'NEARBY_RANGE', 75))
      except (TypeError, ValueError):
        radius_km = radius_km or getattr(settings, 'NEARBY_RANGE', 75)
    else:
      radius_km = radius_km or getattr(settings, 'NEARBY_RANGE', 75)

    nearby_locations = get_nearby_locations(self, radius_km=radius_km, queryset=queryset)
    if hasattr(self, 'request'):
      user = self.request.user
      nearby_locations = [loc for loc in nearby_locations if loc.is_visible_to(user)]
    return nearby_locations

  # ================================================================
  # Access helper for internal fields
  # ================================================================
  def get_address_display(self):
    """Helper to format the address for display."""
    if self.address:
      return self.address.replace(',', '<br>').replace('\n', '<br>')
    return ''
  
  # ================================================================
  # Shorthand access properties for related fields
  # ================================================================
  @property
  def country(self):
    if self.geo:
      return self.geo.country
    return None
  @property
  def region(self):
    if self.geo:
      return self.geo.region
    return None
  @property
  def department(self):
    if self.geo:
      return self.geo.department
    return None
  
  # ================================================================
  # Ajax and API helper methods
  # ================================================================
  @ajax_function
  def topactions(self):
    # Function to allow to render the /function/location/topactions.html 
    # template with the location context for AJAX calls from the frontend.
    return ''
  @ajax_function
  def contact_details(self):
    # Function to allow to render the /function/location/contact_details.html 
    # template with the location context for AJAX calls from the frontend.
    # Handles fields: address, owners_name, phone, email
    return ''