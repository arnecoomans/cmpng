from cmnsd.models import BaseModel, VisibilityModel
from cmnsd.models.BaseMethods import ajax_function


class LocationAccessMixin:
  """
  Visibility-filtered access to a Location's related objects.

  All methods are cached on the instance (e.g. _filtered_comments) and
  respect self.request when set (injected by the CMNSD dispatcher or views).
  """

  # ================================================================
  # Media
  # ================================================================

  @ajax_function
  def ordered_media(self):
    if not hasattr(self, '_ordered_media'):
      """Get media ordered by visibility (private first, public last)."""
      from django.db.models import Case, When, IntegerField
      order_map = {'q': 0, 'f': 1, 'c': 2, 'p': 3}
      whens = [When(visibility=code, then=order) for code, order in order_map.items()]
      queryset = self.media.annotate(
        visibility_order=Case(*whens, default=999, output_field=IntegerField()),
      ).order_by('visibility_order', '-date_created')
      queryset = BaseModel.filter_status(queryset)
      if hasattr(self, 'request'):
        queryset = VisibilityModel.filter_visibility(queryset, request=self.request)
      self._ordered_media = queryset
    return self._ordered_media

  # ================================================================
  # Comments
  # ================================================================

  @ajax_function
  def filtered_comments(self):
    if not hasattr(self, '_filtered_comments'):
      """Return published comments filtered by visibility for the current user."""
      queryset = self.comments.filter(status='p').order_by('-date_created')
      if hasattr(self, 'request'):
        queryset = VisibilityModel.filter_visibility(queryset, request=self.request)
      else:
        queryset = queryset.filter(visibility='p')
      self._filtered_comments = queryset
    return self._filtered_comments

  @ajax_function
  def owned_comments(self):
    if not hasattr(self, '_owned_comments'):
      """Return filtered_comments narrowed to comments owned by the current user."""
      if hasattr(self, 'request') and self.request.user.is_authenticated:
        self._owned_comments = self.filtered_comments().filter(user=self.request.user)
      else:
        self._owned_comments = self.comments.none()
    return self._owned_comments

  # ================================================================
  # Tags
  # ================================================================

  @ajax_function
  def filtered_tags(self):
    if not hasattr(self, '_filtered_tags'):
      """Return tags filtered by visibility for the current user."""
      queryset = self.tags.all()
      if hasattr(self, 'request'):
        queryset = VisibilityModel.filter_visibility(queryset, request=self.request)
      else:
        queryset = queryset.filter(visibility='p')
      self._filtered_tags = queryset
    return self._filtered_tags

  # ================================================================
  # Lists
  # ================================================================

  @ajax_function
  def filtered_lists(self):
    if not hasattr(self, '_filtered_lists'):
      """Return published lists containing this location, filtered by visibility."""
      from locations.models.List import List
      queryset = List.objects.filter(items__location=self, status='p')
      if hasattr(self, 'request'):
        queryset = VisibilityModel.filter_visibility(queryset, request=self.request)
      else:
        queryset = queryset.filter(visibility='p')
      self._filtered_lists = queryset
    return self._filtered_lists

  @ajax_function
  def has_lists(self):
    if not hasattr(self, '_has_lists'):
      """Return True if this location appears in any visible published list."""
      self._has_lists = self.filtered_lists().exists()
    return self._has_lists

  @ajax_function
  def owned_lists(self):
    if not hasattr(self, '_owned_lists'):
      """Return filtered_lists narrowed to lists owned by the current user."""
      if hasattr(self, 'request') and self.request.user.is_authenticated:
        self._owned_lists = self.filtered_lists().filter(user=self.request.user)
      else:
        from locations.models.List import List
        self._owned_lists = List.objects.none()
    return self._owned_lists
