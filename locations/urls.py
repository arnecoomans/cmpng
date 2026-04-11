from django.urls import path

from . import views

app_name = 'locations'

urlpatterns = [
  path('', views.AllLocationListView.as_view(), name='home'),
  
  # Location List Views (views/locations/locations_list.py)
  path('all/', views.AllLocationListView.as_view(), name='all'),
  path('accommodations/', views.AccommodationListView.as_view(), name='accommodations'),
  path('activities/', views.ActivityListView.as_view(), name='activities'),

  # Add Location View (views/locations/add_location.py)
  path('location/add/', views.AddLocationView.as_view(), name='add_location'),

  # Check Duplicate View (views/locations/check_duplicate.py)
  path('location/add/check-duplicate/', views.CheckDuplicateView.as_view(), name='check_duplicate'),

  # Re-enrich Location View (views/locations/reenrich_location.py) — staff only
  path('location/<slug:slug>/re-enrich/', views.ReEnrichLocationView.as_view(), name='reenrich_location'),

  # Revoke Location View (views/locations/revoke_location.py) — staff only
  path('location/<slug:slug>/revoke/', views.RevokeLocationView.as_view(), name='revoke_location'),

  # Location Detail Views (views/locations/location_detail.py)
  path('location/<slug:slug>/', views.LocationDetailView.as_view(), name='location_detail'),
  path('accommodation/<slug:slug>/', views.LocationDetailView.as_view(), name='accommodation_detail'),
  path('activity/<slug:slug>/', views.LocationDetailView.as_view(), name='activity_detail'),

  # Tag Views (views/tags/)
  path('tags/', views.TagListView.as_view(), name='tags'),
  path('tag/<slug:slug>/edit/', views.EditTagView.as_view(), name='edit_tag'),

  # Manage Views (views/*/manage_*.py)
  path('manage/tags/', views.ManageTagVisibilityView.as_view(), name='manage_tag_visibility'),
  path('manage/visits/', views.ManageVisitsView.as_view(), name='manage_visits'),
  path('manage/visits/<slug:slug>/', views.ManageVisitsView.as_view(), name='manage_visits_location'),
  path('manage/media/<slug:slug>/', views.ManageMediaView.as_view(), name='manage_media'),
  path('manage/lists/<slug:slug>/', views.ManageListsView.as_view(), name='manage_lists'),

  # Comment Views (views/comments/)
  path('comments/', views.CommentListView.as_view(), name='comments'),

  # Lists Views (views/lists/)
  path('lists/', views.ListListView.as_view(), name='lists'),
  path('lists/<slug:slug>/', views.ListDetailView.as_view(), name='list_detail'),

  # Preferences View (views/profile/)
  path('preferences/', views.PreferencesView.as_view(), name='preferences'),
  path('preferences/maps-session/revoke/', views.RevokeMapsSessionView.as_view(), name='revoke_maps_session'),
  path('preferences/language/', views.SetLanguageView.as_view(), name='set_language'),
  path('preferences/export/', views.ExportDataView.as_view(), name='export_data'),

  # Page Views (views/pages/)
  path('pages/<slug:slug>/', views.PageDetailView.as_view(), name='page_detail'),

]