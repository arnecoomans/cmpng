# Working on CMPNG

Cmpng is a django 6 application. It lists accommodations and activities in a holiday or day excursion context, allowing to plan activities and overnight stays. 

## What you should know
- Coding syntax: 2 space indents
- With translations:
  - in templates use {% translate 'value'|capfirst %}
  - in python use capfirst(_('value))
  so translations are stored lower-caps whenever possible. Larger blocks of text (blocktranslate) can have caps.

## Dependancies
- cmnsd is a shared app that offers access to
  - cmnsd.api: direct access to field data, that works in multiple django projects.
    - /json/<model>/<object:id>-<object:slug>/<field>/ is the general way to access a field within an object
    - templates are automatically searched
  - cmnsd.js: a js library that allows to fetch data from cmnsd.api and use it
  - cmnsd mixins: there are a few mixins such as FilterMixin that handles filtering by status, visibility and query parameters. Exact field names are used.
  - cmnsd models: some basemodels exist, that other functionality relies on, such as model BaseModel, Visibility Basemodel, and Category, Comment and Tag basemodel.
  - locally hosted statics such as bootstrap, bootstrap icons
  - Resources holds several reusable scripts, such as update and pato (production data to acceptance, test or development)
  - cmnsd is developed and improved within actual projects, so improvements are possible
- Locally sqlite backend is used, on prod postgres is used
- In development (debug=True) the debug toolbar is loaded
- Testing is done with pytest

## Model architecture
- When applicable, try to advise services to keep the model neat
- Use Custom Manager and Queryset for optimized data access to allow preloading and minimize database queries

## About answering questions
First, make sure you have enough information to know what the question is. Ask for more information, expectations, examples or clarifications when needed. Before making changes, summarize the solution. The developer is also the architect and needs to understand how things work. Ensure this is clear before making any change.

## App specific knowledge
- The Location model has a reference to Regions (field: geo).
  - The region model has a field parent. This is used to create hierarchy.
  - Overall the parent__parent is country, parent is region and no parent is concidered department.


## Expectations
I expect you to be a senior analyst and advisor in the setup and architecture of the app. Keep in mind user logic, find the best long-term solution and think of alternatieves. Also, when you make changes, you are concise, precise and honest.
I expect you to offer to update changelog.md when changes are made, and check the documentations folder if other documentation needs to be handled.

Codex will review your output once you are done.

There is also a document claude_extra.md with changes in your own words. Read that as well.