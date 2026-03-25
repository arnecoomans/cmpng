from django.conf import settings

''' Context Processors for CMNS Django Project 

    Add this to your settings.py:
    TEMPLATES = [
      {
        [...]
        'OPTIONS': {
          'context_processors': [
            [...]
            'cmnsdjango.context_processors.setting_data',
          ],
        },
      },
    ]
'''

def setting_data(request):
  ''' Return Context Variables 
      with default fallback values if not set in project/settings.py 
  '''  
  return {
    'nearby_range': getattr(settings, 'NEARBY_RANGE', 75),
    'guest_nearby_range': getattr(settings, 'GUEST_NEARBY_RANGE', 35),
    'lazy_load_media': getattr(settings, 'LAZY_LOAD_MEDIA', False),
    'lazy_load_nearby': getattr(settings, 'LAZY_LOAD_NEARBY', False),
    'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    
  }