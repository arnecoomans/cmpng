from django.utils.translation import gettext_lazy as _

''' Translation Cheat Class
    This class holds translations for often used terms from database content.
    By storing these terms in this class, it will appear via django-admin makemessages -a
    and retain the translations when translating.
'''

class Translations:
  translations = [
    # Countries
    _('Netherlands'),
    _('Belgium'),
    _('Germany'),
    _('France'),
    _('Spain'),
    _('Italy'),
    _('United Kingdom'),
    _('United States'),
    _('Canada'),
    _('Australia'),
    _('Indonesia'),
    _('Portugal'),
    _('Switzerland'),
    _('Austria'),
    _('Denmark'),
    _('Sweden'),
    _('Norway'),
    _('Finland'),
    _('Poland'),
    _('Czech Republic'),
    _('Slovakia'),
    _('Hungary'),
    _('Greece'),
    _('Turkey'),
    _('Croatia'),
    _('Slovenia'),
    _('Luxembourg'),
    _('Ireland'),
    _('Russia'),
    _('Ukraine'),
    _('Romania'),
    _('Bulgaria'),
    _('Serbia'),
    _('Bosnia and Herzegovina'),
    _('North Macedonia'),
    _('Albania'),
    _('Montenegro'),
    _('Cyprus'),
    _('Moldova'),
    _('Belarus'),
    _('Lithuania'),
    _('Latvia'),
    _('Estonia'),
    _('Gibraltar'),
    _('Andorra'),
    _('Monaco'),
    _('Vatican City'),
    _('San Marino'),

    # Regions
    _('Vosges'),
    _('Ardennes'),
    _('Eifel'),
    _('Pyrenees'),

    # Locations
    _('Bed & Breakfast'),
    _('Camping'),
    _('Hotel'),
    _('Chalet'),
    _('Gite'),
    _('Glamping (Safaritent)'),
    _('Mobile Home'),
    _('Resort'),
    _('Villa'),
    _('Resort'),

    # Activities
    _('Sight-to-see'),
    _('Transit (one nighter)'),
    _('Beach'),
    _('Bar or Pub'),
    _('Cafe'),
    _('City'),
    _('Museum'),
    _('Park'),
    _('Playground'),
    _('Rest-stop'),
    _('Restaurant'),
    _('Sauna'),
    _('Shop'),
    _('Swimmingpool'),
    _('Theatre'),
    _('Theme-park'),
    _('Village'),
    _('Walk'),
    _('Winery'),
    _('Zoo'),

    # Other common translations
    
  ]