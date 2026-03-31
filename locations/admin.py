from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Location, Region, Category, Tag, Link, Chain, App, UserPreferences, Visits, Size, List, ListItem, Distance
from .models.Comment import Comment
from .models.Media import Media
from .models.Page import Page


class BaseModelAdmin(admin.ModelAdmin):
    """Base admin for all models inheriting from BaseModel."""
    
    actions = ['recalculate_fields']
    
    def save_model(self, request, obj, form, change):
        """Auto-set user to current user if not already set."""
        if not change:  # Only on creation, not on edit
            if not obj.user:
                obj.user = request.user
        super().save_model(request, obj, form, change)
    
    # Common read-only fields for BaseModel
    readonly_fields = ('token', 'date_created', 'date_modified')
    
    # Common fieldsets structure
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Add BaseModel fields at the bottom
        fieldsets += (
            (_('System Information'), {
                'classes': ('collapse',),
                'fields': ('token', 'status', 'user', 'date_created', 'date_modified'),
            }),
        )
        return fieldsets
    
    @admin.action(description=_('Recalculate computed fields (run save on selected items)'))
    def recalculate_fields(self, request, queryset):
        """Force save() on each object to recalculate computed fields."""
        count = 0
        for obj in queryset:
            obj.save()
            count += 1
        self.message_user(
            request,
            _(f'Successfully recalculated {count} {queryset.model._meta.verbose_name_plural}.'),
        )


@admin.action(description='Recalculate distances')
def recalculate_distances(modeladmin, request, queryset):
    for location in queryset:
        location.calculate_distance_to_departure_center(request=request)
    modeladmin.message_user(request, f'Recalculated {queryset.count()} locations')
    
@admin.register(Location)
class LocationAdmin(BaseModelAdmin):
    list_display = ('name', 'geo', 'chain', 'is_accommodation', 'is_activity', 'status', 'distance_to_departure_center')
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
        (_('Visibility'), {
            'fields': ('visibility',),
        }),
    )
    
    readonly_fields = BaseModelAdmin.readonly_fields + ('is_accommodation', 'is_activity', 'distance_to_departure_center', 'google_place_id')
    actions = BaseModelAdmin.actions + [recalculate_distances]


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
class CategoryAdmin(BaseModelAdmin):
    list_display = ('name', 'parent', 'status')
    list_filter = ('status',)
    search_fields = ('name',)
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent',)
        }),
    )


@admin.register(Tag)
class TagAdmin(BaseModelAdmin):
    list_display = ('name', 'parent', 'status', 'visibility')
    list_filter = ('status', 'visibility')
    search_fields = ('name', 'description')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        (_('Visibility'), {
            'fields': ('visibility',),
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
    list_display = ('user', 'location', 'year', 'month', 'day')
    search_fields = ('user__username', 'location__name')
    list_filter = ('year', 'month')
    
    fieldsets = (
        (_('Visit Information'), {
            'fields': ('user', 'location', 'year', 'month', 'day')
        }),
    )
@admin.register(Comment)
class CommentAdmin(BaseModelAdmin):
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
        (_('Visibility'), {
            'fields': ('visibility',),
        }),
    )


@admin.register(Media)
class MediaAdmin(BaseModelAdmin):
    list_display = ('__str__', 'location', 'visibility', 'status', 'date_created')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'location__name')

    fieldsets = (
        (_('Media'), {
            'fields': ('location', 'source', 'title'),
        }),
        (_('Visibility'), {
            'fields': ('visibility',),
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
class ListAdmin(BaseModelAdmin):
    list_display = ('name', 'template', 'visibility', 'is_archived', 'user', 'status', 'date_created')
    list_filter = ('template', 'visibility', 'is_archived', 'status')
    search_fields = ('name', 'description')
    inlines = (ListItemInline,)

    fieldsets = (
        (_('List'), {
            'fields': ('name', 'description', 'template', 'is_archived'),
        }),
        (_('Visibility'), {
            'fields': ('visibility',),
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
class PageAdmin(BaseModelAdmin):
  list_display = ('title', 'slug', 'visibility', 'status')
  list_filter = ('status', 'visibility')
  search_fields = ('title', 'body')
  prepopulated_fields = {'slug': ('title',)}

  fieldsets = (
    (_('Content'), {
      'fields': ('title', 'slug', 'body'),
    }),
    (_('Visibility'), {
      'fields': ('visibility',),
    }),
  )