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

  # Re-enrich Location View (views/locations/reenrich_location.py) — staff only
  path('location/<slug:slug>/re-enrich/', views.ReEnrichLocationView.as_view(), name='reenrich_location'),

  # Location Detail Views (views/locations/location_detail.py)
  path('location/<slug:slug>/', views.LocationDetailView.as_view(), name='location_detail'),
  path('accommodation/<slug:slug>/', views.LocationDetailView.as_view(), name='accommodation_detail'),
  path('activity/<slug:slug>/', views.LocationDetailView.as_view(), name='activity_detail'),

  # Tag Views (views/tags/)
  path('tags/', views.TagListView.as_view(), name='tags'),

  # Manage Visits View (views/visits/manage_visits.py)
  path('visits/manage/', views.ManageVisitsView.as_view(), name='manage_visits'),
  path('visits/manage/<slug:slug>/', views.ManageVisitsView.as_view(), name='manage_visits_location'),

  # Comment Views (views/comments/)
  path('comments/', views.CommentListView.as_view(), name='comments'),

  # Media View (views/media/)
  path('media/manage/<slug:slug>/', views.ManageMediaView.as_view(), name='manage_media'),

  # Lists Views (views/lists/)
  path('lists/', views.ListListView.as_view(), name='lists'),
  path('lists/<slug:slug>/', views.ListDetailView.as_view(), name='list_detail'),
  path('lists/manage/<slug:slug>/', views.ManageListsView.as_view(), name='manage_lists'),

  # Preferences View (views/profile/)
  path('preferences/', views.PreferencesView.as_view(), name='preferences'),
  path('preferences/maps-session/revoke/', views.RevokeMapsSessionView.as_view(), name='revoke_maps_session'),

]