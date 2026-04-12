from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Location, Region, Category, Tag, Link, Chain, App, UserPreferences, Size, List, ListItem, Distance
from .models.Visits import Visits
from .models.Comment import Comment
from .models.Media import Media
from .models.Page import Page
from cmnsd.admin import BaseModelAdmin, VisibilityModelAdmin, TranslationAliasAdminMixin
from locations.services.visits_recommendation import get_recommendation_summary


@admin.action(description='Recalculate distances')
def recalculate_distances(modeladmin, request, queryset):
    for location in queryset:
        location.calculate_distance_to_departure_center(request=request)
    modeladmin.message_user(request, f'Recalculated {queryset.count()} locations')


@admin.register(Location)
class LocationAdmin(VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('name', 'geo', 'chain', 'completeness', 'distance_to_departure_center', 'recommendation_score')
    list_filter = ('is_accommodation', 'is_activity', 'status', 'visibility', 'geo')
    search_fields = ('name', 'summary', 'address', 'email')
    filter_horizontal = ('categories', 'tags')

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'summary', 'description', 'slug', 'geo', 'chain', 'size')
        }),
        (_('Contact Details'), {
            'fields': ('address', 'email', 'phone', 'owners_name')
        }),
        (_('Coordinates'), {
            'fields': ('coord_lat', 'coord_lon', 'google_place_id', 'distance_to_departure_center'),
        }),
        (_('Classification'), {
            'fields': ('categories', 'tags', 'is_accommodation', 'is_activity'),
        }),
    )

    readonly_fields = BaseModelAdmin.readonly_fields + ('is_accommodation', 'is_activity', 'distance_to_departure_center', 'google_place_id')
    actions = BaseModelAdmin.actions + [recalculate_distances]

    @admin.display(description=_('Score'))
    def recommendation_score(self, obj):
        summary = get_recommendation_summary(obj)
        if summary['score'] is None:
            return '–'
        return summary['score']


@admin.register(Region)
class RegionAdmin(BaseModelAdmin):
    list_display = ('name', 'parent', 'level', 'status', 'cached_average_distance_to_center')
    list_filter = ('level', 'status')
    search_fields = ('name',)

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent')
        }),
    )

    readonly_fields = BaseModelAdmin.readonly_fields + ('level',)


@admin.register(Category)
class CategoryAdmin(TranslationAliasAdminMixin, BaseModelAdmin):
    list_display = ('name', 'parent', 'status')
    list_filter = ('status',)
    search_fields = ('name',)

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent',)
        }),
    )


@admin.register(Tag)
class TagAdmin(TranslationAliasAdminMixin, VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('name', 'parent', 'status', 'visibility', 'similarity_weight')
    list_filter = ('status', 'visibility')
    search_fields = ('name', 'description')

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        (_('Similarity'), {
            'fields': ('similarity_weight',),
        }),
    )


@admin.register(Link)
class LinkAdmin(BaseModelAdmin):
    list_display = ('__str__', 'location', 'url', 'status')
    list_filter = ('status',)
    search_fields = ('url', 'label')

    fieldsets = (
        (_('Link Information'), {
            'fields': ('location', 'url', 'label')
        }),
    )


@admin.register(Chain)
class ChainAdmin(BaseModelAdmin):
    list_display = ('name', 'parent', 'status')
    list_filter = ('status',)
    search_fields = ('name',)

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent')
        }),
    )


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'url_format', 'default_enabled')
    search_fields = ('label', 'slug')
    list_filter = ('default_enabled',)

    fieldsets = (
        (_('App Information'), {
            'fields': ('label', 'slug', 'url_format', 'default_enabled', 'category')
        }),
    )


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'home', 'external_maps_consent')
    search_fields = ('user__username',)

    fieldsets = (
        (_('User Preferences'), {
            'fields': ('user', 'home', 'family', 'external_maps_consent', 'favorites', 'hidden_locations', 'apps')
        }),
    )


@admin.register(Visits)
class VisitsAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'year', 'month', 'day', 'end_year', 'end_month', 'end_day', 'recommendation_label')
    search_fields = ('user__username', 'location__name')
    list_filter = ('year', 'month', 'recommendation')

    fieldsets = (
        (_('Visit Information'), {
            'fields': ('user', 'location')
        }),
        (_('Start date'), {
            'fields': ('year', 'month', 'day')
        }),
        (_('End date'), {
            'fields': ('end_year', 'end_month', 'end_day'),
            'description': _('Optional — leave blank for single-day or unknown duration visits.'),
        }),
        (_('Recommendation'), {
            'fields': ('recommendation',),
        }),
    )

    _RECOMMENDATION_LABELS = {
        Visits.RECOMMENDATION_RECOMMEND: _('Recommended'),
        Visits.RECOMMENDATION_NEUTRAL: _('Neutral'),
        Visits.RECOMMENDATION_DO_NOT_RECOMMEND: _('Not recommended'),
    }

    @admin.display(description=_('Recommendation'))
    def recommendation_label(self, obj):
        if obj.recommendation is None:
            return '–'
        return self._RECOMMENDATION_LABELS.get(obj.recommendation, obj.recommendation)


@admin.register(Comment)
class CommentAdmin(VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('get_title', 'content_type', 'object_id', 'user', 'visibility', 'status')
    list_filter = ('status', 'visibility', 'content_type')
    search_fields = ('text', 'title', 'user__username')
    readonly_fields = BaseModelAdmin.readonly_fields + ('content_type', 'object_id', 'content_object')

    fieldsets = (
        (_('Comment'), {
            'fields': ('title', 'text')
        }),
        (_('Attached to'), {
            'fields': ('content_type', 'object_id', 'content_object'),
        }),
    )


@admin.register(Media)
class MediaAdmin(VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('__str__', 'location', 'visibility', 'status', 'date_created')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'location__name')
    readonly_fields = BaseModelAdmin.readonly_fields + ('file_hash',)

    fieldsets = (
        (_('Media'), {
            'fields': ('location', 'source', 'title'),
        }),
    )


@admin.register(Size)
class SizeAdmin(BaseModelAdmin):
    list_display = ['name', 'code', 'description', 'order', 'status']
    list_filter = ['status', 'categories']
    filter_horizontal = ['categories']


class ListItemInline(admin.TabularInline):
    model = ListItem
    extra = 0
    fields = ('order', 'location', 'note', 'stay_duration', 'price_per_night', 'media', 'leg_distance')
    readonly_fields = ('leg_distance',)
    ordering = ('order',)
    autocomplete_fields = ('location',)


@admin.register(List)
class ListAdmin(VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('name', 'template', 'visibility', 'is_archived', 'user', 'status', 'date_created')
    list_filter = ('template', 'visibility', 'is_archived', 'status')
    search_fields = ('name', 'description')
    inlines = (ListItemInline,)

    fieldsets = (
        (_('List'), {
            'fields': ('name', 'description', 'template', 'is_archived'),
        }),
    )


@admin.register(ListItem)
class ListItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'list', 'location', 'order', 'stay_duration', 'price_per_night')
    list_filter = ('list__template',)
    search_fields = ('location__name', 'list__name', 'note')
    autocomplete_fields = ('location',)
    readonly_fields = ('leg_distance',)

    fieldsets = (
        (_('Item'), {
            'fields': ('list', 'location', 'order', 'note'),
        }),
        (_('Accommodation'), {
            'fields': ('stay_duration', 'price_per_night'),
        }),
        (_('Media & Routing'), {
            'fields': ('media', 'leg_distance'),
        }),
    )


@admin.register(Distance)
class DistanceAdmin(admin.ModelAdmin):
    list_display = ('origin', 'destination', 'distance_m', 'duration_s', 'cached_at')
    search_fields = ('origin__name', 'destination__name')
    readonly_fields = ('cached_at',)

    fieldsets = (
        (_('Route'), {
            'fields': ('origin', 'destination'),
        }),
        (_('Cached result'), {
            'fields': ('distance_m', 'duration_s', 'cached_at'),
        }),
    )


@admin.register(Page)
class PageAdmin(VisibilityModelAdmin, BaseModelAdmin):
    list_display = ('title', 'slug', 'visibility', 'status')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}

    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'slug', 'body'),
        }),
    )
