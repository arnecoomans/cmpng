from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Length
from django.views.generic import TemplateView

from locations.models.Location import Location
from locations.models.Comment import Comment
from locations.models.Tag import Tag


class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
  """Staff-only dashboard surfacing locations that may need attention."""

  template_name = 'staff/dashboard.html'

  max_results = 15

  def test_func(self):
    return self.request.user.is_staff

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['max_results'] = self.max_results

    published = Location.objects.filter(status='p').exclude(categories__slug='home').select_related('geo')

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
    fewest_cats_qs = (
      published
      .annotate(cat_count=Count('categories'))
      .order_by('cat_count', 'name')
    )
    first_ten_cats = list(fewest_cats_qs[:10])
    cat_boundary = first_ten_cats[-1].cat_count if first_ten_cats else 0
    context['fewest_categories'] = fewest_cats_qs.filter(cat_count__lte=cat_boundary)
    context['fewest_categories_boundary'] = cat_boundary
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
    context['revoked'] = (
      revoked_qs
      .select_related('geo')
      .prefetch_related(
        Prefetch(
          'comments',
          queryset=Comment.objects.filter(status='p', title__icontains='revok').order_by('-date_created'),
          to_attr='revoke_comments',
        )
      )
      .order_by('-date_modified')[:self.max_results]
    )

    return context
