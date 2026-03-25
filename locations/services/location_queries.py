from django.db.models import Count

def get_tags_from_queryset(queryset, limit=20, min_usage=1):
    """
    Get unique tags from a location queryset, ordered by usage.
    
    Args:
        queryset: Location queryset
        limit: Maximum number of tags (None = unlimited)
        min_usage: Minimum locations that must use the tag
    
    Returns:
        QuerySet of dicts with id, slug, name, location_count
    """
    from locations.models import Tag
    
    tags_qs = Tag.objects.filter(
        locations__in=queryset,
        status='p'
    ).annotate(
        location_count=Count('locations', distinct=True)
    ).filter(
        location_count__gte=min_usage
    ).order_by('-location_count', 'name').values(
        'id', 'slug', 'name', 'location_count'
    )
    
    if limit:
        tags_qs = tags_qs[:limit]
    
    return tags_qs


def get_categories_from_queryset(queryset, limit=20, min_usage=1):
    """Get unique categories from a location queryset, ordered by usage."""
    from locations.models import Category
    
    categories_qs = Category.objects.filter(
        locations__in=queryset,
        status='p'
    ).annotate(
        location_count=Count('locations', distinct=True)
    ).filter(
        location_count__gte=min_usage
    ).order_by('-location_count', 'name').values(
        'id', 'slug', 'name', 'location_count'
    )
    
    if limit:
        categories_qs = categories_qs[:limit]
    
    return categories_qs


def get_countries_with_locations(queryset=None):
    """Get all countries that have locations."""
    from locations.models import Location
    
    if queryset is None:
        queryset = Location.objects.all()
    
    return queryset.exclude(
        geo__parent__parent__isnull=True
    ).values(
        'geo__parent__parent__id',
        'geo__parent__parent__slug',
        'geo__parent__parent__name'
    ).distinct().order_by('geo__parent__parent__name')

def get_regions_with_locations(queryset=None):
    """Get all regions that have locations."""
    from locations.models import Location

    if queryset is None:
        queryset = Location.objects.all()

    return queryset.exclude(
        geo__parent__isnull=True
    ).values(
        'geo__parent__id',
        'geo__parent__slug',
        'geo__parent__name'
    ).distinct().order_by('geo__parent__name')

def get_departments_with_locations(queryset=None):
    """Get all departments that have locations."""
    from locations.models import Location

    if queryset is None:
        queryset = Location.objects.all()

    return queryset.exclude(
        geo__isnull=True
    ).values(
        'geo__id',
        'geo__slug',
        'geo__name'
    ).distinct().order_by('geo__name')

def get_sizes_for_categories(category_ids):
    """Get available sizes for given categories."""
    from locations.models import Size
    
    return Size.objects.filter(
        categories__id__in=category_ids,
        status='p'
    ).distinct().order_by('order', 'name')