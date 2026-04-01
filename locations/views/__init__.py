from .locations import AllLocationListView, AccommodationListView, ActivityListView, LocationDetailView, AddLocationView, ReEnrichLocationView, CheckDuplicateView, RevokeLocationView
from .tags import TagListView, ManageTagVisibilityView
from .visits import ManageVisitsView
from .comments import CommentListView
from .profile import PreferencesView, RevokeMapsSessionView, SetLanguageView
from .media import ManageMediaView
from .lists import ManageListsView, ListListView, ListDetailView
from .pages import PageDetailView
from .Translations import *

__all__ = [
  'AllLocationListView', 'AccommodationListView', 'ActivityListView',
  'LocationDetailView', 'AddLocationView', 'ReEnrichLocationView', 'CheckDuplicateView', 'RevokeLocationView',
  'TagListView', 'ManageTagVisibilityView',
  'ManageVisitsView',
  'CommentListView',
  'PreferencesView', 'RevokeMapsSessionView', 'SetLanguageView',
  'ManageMediaView',
  'ManageListsView', 'ListListView', 'ListDetailView',
  'PageDetailView',
]