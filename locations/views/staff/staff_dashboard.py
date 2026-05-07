from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Length
from django.views.generic import TemplateView

from locations.models.Location import Location
from locations.models.Comment import Comment
from locations.models.Tag import Tag


class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
  """Staff-only dashboard surfacing locations that may need attention."""

  template_name = 'staff/dashboard.html'

  max_results = 35

  def test_func(self):
    return self.request.user.is_staff

  def _completeness_context(self, published):
    from django.db.models import Avg
    total = published.count()
    stats = published.aggregate(
      avg=Avg('completeness'),
      low=Count('pk', filter=Q(completeness__lt=50)),
      mid=Count('pk', filter=Q(completeness__gte=50, completeness__lt=75)),
      high=Count('pk', filter=Q(completeness__gte=75, completeness__lt=100)),
      perfect=Count('pk', filter=Q(completeness=100)),
    )
    ctx = {
      'completeness_total': total,
      'completeness_avg': round(stats['avg'] or 0),
      'completeness_low_count': stats['low'],
      'completeness_mid_count': stats['mid'],
      'completeness_high_count': stats['high'],
      'completeness_perfect_count': stats['perfect'],
    }
    if total:
      ctx['completeness_low_pct'] = round(stats['low'] * 100 / total)
      ctx['completeness_mid_pct'] = round(stats['mid'] * 100 / total)
      ctx['completeness_high_pct'] = round(stats['high'] * 100 / total)
      ctx['completeness_perfect_pct'] = round(stats['perfect'] * 100 / total)
    else:
      ctx['completeness_low_pct'] = ctx['completeness_mid_pct'] = 0
      ctx['completeness_high_pct'] = ctx['completeness_perfect_pct'] = 0
    return ctx

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['max_results'] = self.max_results

    published = Location.objects.filter(status='p').exclude(categories__slug='home').select_related('geo')
    context.update(self._completeness_context(published))

    problems_qs = published.filter(Q(address__isnull=True) | Q(address='') | Q(geo__isnull=True))
    context['problems_count'] = problems_qs.count()
    context['problems'] = problems_qs.order_by('name')[:self.max_results]

    context['lowest_completeness'] = (
      published
      .select_related('geo__parent__parent')
      .prefetch_related('categories')
      .order_by('completeness', 'name')[:self.max_results]
    )

    missing_summary_qs = (
      published
      .annotate(summary_len=Length('summary'))
      .filter(Q(summary__isnull=True) | Q(summary_len__lt=50))
    )
    context['missing_summary_count'] = missing_summary_qs.count()
    context['missing_summary'] = (
      missing_summary_qs
      .select_related('geo__parent__parent')
      .prefetch_related('categories')
      .order_by('name')[:self.max_results]
    )

    missing_description_qs = published.filter(Q(description='') | Q(description__isnull=True))
    context['missing_description_count'] = missing_description_qs.count()
    context['missing_description'] = missing_description_qs.order_by('name')[:self.max_results]
    fewest_tags_qs = (
      published
      .annotate(tag_count=Count('tags'))
      .order_by('tag_count', 'name')
    )
    first_ten_tags = list(fewest_tags_qs[:10])
    tag_boundary = first_ten_tags[-1].tag_count if first_ten_tags else 0
    context['fewest_tags'] = fewest_tags_qs.filter(tag_count__lte=tag_boundary)
    context['fewest_tags_boundary'] = tag_boundary
    from locations.models.Category import Category
    context['category_usage'] = (
      Category.objects
      .filter(status='p', children__isnull=True)
      .annotate(location_count=Count('locations', filter=Q(locations__status='p')))
      .order_by('location_count', 'name')
    )
    active_child_tags = Tag.objects.filter(parent=OuterRef('pk')).exclude(status='x')
    context['tag_usage'] = (
      Tag.objects
      .filter(status='p')
      .annotate(
        has_active_child=Exists(active_child_tags),
        location_count=Count('locations', filter=Q(locations__status='p')),
        revoked_count=Count('locations', filter=Q(locations__status='r')),
      )
      .filter(has_active_child=False)
      .order_by('location_count', 'name')
    )
    location_ct = ContentType.objects.get_for_model(Location)
    latest_comment_date = (
      Comment.objects
      .filter(content_type=location_ct, object_id=OuterRef('pk'), status='p')
      .order_by('-date_created')
      .values('date_created')[:1]
    )
    context['recently_commented'] = (
      Location.objects.filter(status='p').exclude(categories__slug='home')
      .annotate(latest_comment_date=Subquery(latest_comment_date))
      .filter(latest_comment_date__isnull=False)
      .prefetch_related(
        Prefetch(
          'comments',
          queryset=Comment.objects.filter(status='p').order_by('-date_created'),
          to_attr='recent_comments_list',
        )
      )
      .order_by('-latest_comment_date')[:self.max_results]
    )

    context['recently_added'] = (
      published
      .select_related('user')
      .order_by('-date_created')[:self.max_results]
    )
    revoked_qs = Location.objects.filter(status='r')
    context['revoked_count'] = revoked_qs.count()
    has_revoke_comment = Comment.objects.filter(
      content_type=location_ct,
      object_id=OuterRef('pk'),
      status='p',
      title__icontains='revok',
    )
    context['revoked'] = (
      revoked_qs
      .annotate(has_revoke_reason=Exists(has_revoke_comment))
      .select_related('geo')
      .prefetch_related(
        Prefetch(
          'comments',
          queryset=Comment.objects.filter(status='p', title__icontains='revok').order_by('-date_created'),
          to_attr='revoke_comments',
        )
      )
      .order_by('has_revoke_reason', '-date_modified')
    )

    from django.contrib.auth import get_user_model
    context['users'] = get_user_model().objects.order_by('-last_login', 'username')

    return context
