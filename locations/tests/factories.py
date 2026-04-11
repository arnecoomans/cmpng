import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from locations.models import Location, Region, Category, Tag, Link, Chain, List, ListItem, Distance, Media
from locations.models.Size import Size
from locations.models.Comment import Comment
from locations.models.Page import Page
from locations.models.Preferences import UserPreferences
from locations.models.Visits import Visits


User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    name = factory.Sequence(lambda n: f'Location {n}')
    slug = factory.Sequence(lambda n: f'location-{n}')
    status = 'p'
    visibility = 'p'
    user = factory.SubFactory(UserFactory)
    geo = None

    # Optional fields
    address = None
    email = None
    phone = None
    owners_name = None
    coord_lat = None
    coord_lon = None
    
    # Note: categories M2M is handled in tests via location.categories.add()

class SizeFactory(DjangoModelFactory):
    class Meta:
        model = Size

    code = factory.Sequence(lambda n: f'S{n}')
    name = factory.Sequence(lambda n: f'Size {n}')
    order = 0

class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    name = factory.Sequence(lambda n: f'Region {n}')
    slug = factory.Sequence(lambda n: f'region-{n}')  # was LazyAttribute
    status = 'p'
    visibility = 'p'
    user = factory.SubFactory(UserFactory)
    parent = None

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    status = 'p'
    user = factory.SubFactory(UserFactory)
    parent = None

class TagFactory(DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f'Tag {n}')
    slug = factory.Sequence(lambda n: f'tag-{n}')
    status = 'p'
    visibility = 'p'
    user = factory.SubFactory(UserFactory)
    parent = None

class LinkFactory(DjangoModelFactory):
    class Meta:
        model = Link

    url = factory.Sequence(lambda n: f'https://example-{n}.com')
    label = factory.Sequence(lambda n: f'Link {n}')
    location = factory.SubFactory(LocationFactory)
    status = 'p'
    user = factory.SubFactory(UserFactory)

class SizeFactory(DjangoModelFactory):
    class Meta:
        model = Size

    name = factory.Sequence(lambda n: f'Size {n}')
    code = factory.Sequence(lambda n: f'S{n}')
    status = 'p'
    order = factory.Sequence(lambda n: n)


class ChainFactory(DjangoModelFactory):
    class Meta:
        model = Chain

    name = factory.Sequence(lambda n: f'Chain {n}')
    slug = factory.Sequence(lambda n: f'chain-{n}')
    status = 'p'
    user = factory.SubFactory(UserFactory)
    parent = None


class UserPreferencesFactory(DjangoModelFactory):
    class Meta:
        model = UserPreferences

    user = factory.SubFactory(UserFactory)


def make_image_file(name='test.jpg', fmt='JPEG'):
    """Return a SimpleUploadedFile containing a minimal valid image."""
    buf = BytesIO()
    Image.new('RGB', (1, 1), color=(255, 0, 0)).save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


class MediaFactory(DjangoModelFactory):
    class Meta:
        model = Media

    source     = factory.LazyFunction(lambda: make_image_file())
    title      = factory.Sequence(lambda n: f'Photo {n}')
    location   = factory.SubFactory(LocationFactory)
    visibility = 'p'
    status     = 'p'
    user       = factory.SubFactory(UserFactory)


class DistanceFactory(DjangoModelFactory):
    class Meta:
        model = Distance

    origin      = factory.SubFactory(LocationFactory)
    destination = factory.SubFactory(LocationFactory)
    distance_m  = 100000.0
    duration_s  = 4500.0


class ListFactory(DjangoModelFactory):
    class Meta:
        model = List

    name     = factory.Sequence(lambda n: f'List {n}')
    status   = 'p'
    visibility = 'p'
    template = List.TEMPLATE_ITINERARY
    user     = factory.SubFactory(UserFactory)


class ListItemFactory(DjangoModelFactory):
    class Meta:
        model = ListItem

    list     = factory.SubFactory(ListFactory)
    location = factory.SubFactory(LocationFactory)
    order    = factory.Sequence(lambda n: n)


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    text = factory.Sequence(lambda n: f'Comment text {n}')
    title = ''
    status = 'p'
    visibility = 'c'
    user = factory.SubFactory(UserFactory)

    # content_type and object_id must be set explicitly in tests:
    # CommentFactory(content_type=ct, object_id=location.pk)


class VisitsFactory(DjangoModelFactory):
  class Meta:
    model = Visits

  user = factory.SubFactory(UserFactory)
  location = factory.SubFactory(LocationFactory)
  year = 2024
  recommendation = None


class PageFactory(DjangoModelFactory):
    class Meta:
        model = Page

    slug = factory.Sequence(lambda n: f'page-{n}')
    language = 'en'
    title = factory.Sequence(lambda n: f'Page {n}')
    body = 'Page body.'
    status = 'p'
    visibility = 'p'
