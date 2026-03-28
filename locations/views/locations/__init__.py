from .locations_list import AllLocationListView, AccommodationListView, ActivityListView
from .location_detail import LocationDetailView
from .add_location import AddLocationView
from .reenrich_location import ReEnrichLocationView
from .check_duplicate import CheckDuplicateView

__all__ = [
  'AllLocationListView', 'AccommodationListView', 'ActivityListView',
  'LocationDetailView',
  'AddLocationView',
  'ReEnrichLocationView',
  'CheckDuplicateView',
]