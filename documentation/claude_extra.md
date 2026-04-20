# CMPNG — Extra Context for Claude

## Common Gotchas

- After `categories.add()`, always call `location._update_types()` then `location.save()`
- Always call `refresh_from_db()` after `save()` in tests
- Use `status='p', visibility='p'` in test factories — defaults are not public

## Test Conventions

- Factory Boy only — never create model objects manually in tests
- Always use a full 3-level region hierarchy: Country → Region → Department
- Test commands: `pytest locations/tests/ -v` (full suite takes ~12 minutes)

## BaseModel Fields (all models inherit)

- `token` — unique 10-char public ID (auto-generated)
- `status` — `'c'`=concept, `'p'`=published, `'r'`=revoked, `'x'`=deleted
- `date_created`, `date_modified` — auto timestamps
- `user` — ForeignKey to User (nullable)

## VisibilityModel Field (opt-in)

- `visibility` — `'p'`=public, `'c'`=community, `'f'`=family, `'q'`=private

## cmnsd Dispatcher Pattern

- `obj.request = request` must be set before calling `@searchable_function` methods
- FilterMixin does this automatically in its queryset loop; manual calls must do it explicitly

## Translation Conventions

- Store strings lowercase: `_('add location')` not `_('Add Location')`
- Templates: `{% translate 'value'|capfirst %}`
- Python: `capfirst(_('value'))`
- Larger blocks (`blocktranslate`) may use sentence case
