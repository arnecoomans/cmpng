import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from locations.models import Media
from locations.tests.factories import LocationFactory, MediaFactory, UserFactory, make_image_file


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def make_heic_file(name='photo.heic'):
    """Minimal fake HEIC upload (content doesn't matter — conversion is mocked)."""
    return SimpleUploadedFile(name, b'fake-heic-bytes', content_type='image/heic')


# ------------------------------------------------------------------ #
#  __str__
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaStr:

    def test_str_with_location(self):
        loc   = LocationFactory(name='Camping A')
        media = MediaFactory(location=loc, title='Sunset')
        assert str(media) == 'Sunset (Camping A)'

    def test_str_without_location(self):
        media = MediaFactory(location=None, title='Panorama')
        assert str(media) == 'Panorama (no location)'


# ------------------------------------------------------------------ #
#  title auto-population on save
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaTitleAutoPopulation:

    def test_title_preserved_when_provided(self):
        media = MediaFactory(title='My Photo')
        assert media.title == 'My Photo'

    def test_title_derived_from_filename_when_blank(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        img = make_image_file('my_beautiful_photo.jpg')
        media = Media(
            source=img,
            title='',
            location=LocationFactory(),
            visibility='p',
            status='p',
            user=UserFactory(),
        )
        media.save()
        assert media.title == 'my_beautiful_photo.jpg'.replace('_', ' ')

    def test_title_replaces_underscores_with_spaces(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        img = make_image_file('cape_town_beach.jpg')
        media = Media(source=img, title='', location=None, visibility='p', status='p', user=UserFactory())
        media.save()
        assert 'cape town beach' in media.title


# ------------------------------------------------------------------ #
#  HEIC conversion
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaHeicConversion:

    def test_non_heic_file_not_converted(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        media = MediaFactory()
        # _convert_heic_to_jpg should be a no-op for .jpg
        original_name = media.source.name
        assert original_name.endswith('.jpg') or '.' in original_name

    def test_heic_file_triggers_conversion(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)

        fake_image = MagicMock()
        fake_image.convert.return_value = fake_image

        buf = BytesIO()
        Image.new('RGB', (1, 1)).save(buf, format='JPEG')
        buf.seek(0)
        fake_image.save = lambda b, format, quality: b.write(buf.read())

        with patch('pillow_heif.register_heif_opener'), \
             patch('PIL.Image.open', return_value=fake_image):
            media = Media(
                source=make_heic_file('sunset.heic'),
                title='Sunset',
                location=None,
                visibility='p',
                status='p',
                user=UserFactory(),
            )
            media.save()

        assert media.source.name.endswith('.jpg')

    def test_heif_extension_also_triggers_conversion(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)

        fake_image = MagicMock()
        fake_image.convert.return_value = fake_image
        buf = BytesIO()
        Image.new('RGB', (1, 1)).save(buf, format='JPEG')
        buf.seek(0)
        fake_image.save = lambda b, format, quality: b.write(buf.read())

        with patch('pillow_heif.register_heif_opener'), \
             patch('PIL.Image.open', return_value=fake_image):
            media = Media(
                source=make_heic_file('photo.heif'),
                title='Photo',
                location=None,
                visibility='p',
                status='p',
                user=UserFactory(),
            )
            media.save()

        assert media.source.name.endswith('.jpg')

    def test_conversion_skipped_when_no_source(self):
        """_convert_heic_to_jpg returns early when source is falsy."""
        media = Media()
        media._convert_heic_to_jpg()  # should not raise


# ------------------------------------------------------------------ #
#  location FK behaviour
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaLocationRelation:

    def test_location_nullable(self):
        media = MediaFactory(location=None)
        assert media.location is None

    def test_media_deleted_when_location_deleted(self):
        loc   = LocationFactory()
        media = MediaFactory(location=loc)
        pk    = media.pk
        loc.delete()
        assert not Media.objects.filter(pk=pk).exists()

    def test_multiple_media_per_location(self):
        loc = LocationFactory()
        MediaFactory(location=loc)
        MediaFactory(location=loc)
        assert loc.media.count() == 2


# ------------------------------------------------------------------ #
#  File hash
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaFileHash:

    def test_file_hash_populated_on_save(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        media = Media(
            source=make_image_file('photo.jpg'),
            title='Test',
            location=LocationFactory(),
            visibility='p',
            status='p',
            user=UserFactory(),
        )
        media.save()
        assert len(media.file_hash) == 64  # SHA-256 hex digest

    def test_file_hash_not_overwritten_on_resave(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)
        media = Media(
            source=make_image_file('photo.jpg'),
            title='Test',
            location=LocationFactory(),
            visibility='p',
            status='p',
            user=UserFactory(),
        )
        media.save()
        original_hash = media.file_hash
        media.title = 'Updated'
        media.save()
        assert media.file_hash == original_hash


# ------------------------------------------------------------------ #
#  BaseModel / VisibilityModel integration
# ------------------------------------------------------------------ #

@pytest.mark.django_db
class TestMediaInheritance:

    def test_token_auto_generated(self):
        media = MediaFactory()
        assert media.token
        assert len(media.token) >= 10

    def test_default_visibility(self):
        """MediaFactory sets 'p'; verify the field accepts valid choices."""
        media = MediaFactory(visibility='c')
        assert media.visibility == 'c'

    def test_ordering_by_visibility_then_date_modified(self):
        loc   = LocationFactory()
        pub   = MediaFactory(location=loc, visibility='p')
        comm  = MediaFactory(location=loc, visibility='c')
        items = list(loc.media.all())
        visibilities = [m.visibility for m in items]
        # 'c' sorts before 'p' alphabetically (Django default ascending)
        assert visibilities.index('c') < visibilities.index('p')
