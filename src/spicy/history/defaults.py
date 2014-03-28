import itertools
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from .utils import observe


(
    ACTION_CREATE, ACTION_EDIT, ACTION_DELETE, ACTION_ROLLBACK,
    ACTION_RENAME, ACTION_TRASH, ACTION_RESTORE
) = range(7)

ACTION_TYPES = (
    (ACTION_CREATE, _('Created object')),
    (ACTION_EDIT, _('Edited object')),
    (ACTION_DELETE, _('Deleted object')),
    (ACTION_ROLLBACK, _('Rollback')),
    (ACTION_RENAME, _('Renamed object')),
    (ACTION_TRASH, _('Moved to trash')),
    (ACTION_RESTORE, _('Restored from trash')),
)

OBSERVED_FIELDS = getattr(
    settings, 'OBSERVED_FIELDS',
    {'presscenter.Document': (
        'body', 'slug', 'title', 'template', 'tag_template', 'issue_key',
        'pub_date', 'announce', 'sub_title', 'source', 'quote', 'is_public',
        'is_proofread', 'is_prepaid'),
     'xtag.Tag': (
         'template', 'doc_template'),
     'siteskin.HTMLContentProviderModel': ('html',),
     'siteskin.ContentBlock': ('title', 'slug'),
     'mediacenter.Media': ('title', 'desc')
     })

OBSERVED_FIELD_NAMES = list(set(itertools.chain(OBSERVED_FIELDS.values())))

TIMELINE_FIELDS = {
    observe('presscenter.Document', create=True, edit=True, delete=True): (
        'body',),

    observe('xtag.Tag', create=True, edit=True): ('title', 'body'),

    observe('maps.MapProviderModel', create=True, edit=True, delete=True): (
        'title', 'desc', 'geo'),

    observe('event.Event', create=True, edit=True, delete=True): (
        'source', 'title', 'body'),

    observe('extprofile.Profile', create=True): ('first_name', 'last_name'),
    observe('comments.Topic', create=True): ('title', 'body')
}

TIMELINE_PAGE_DAYS = getattr(settings, 'TIMELINE_PAGE_DAYS', 7)

#OBSERVED_FIELDS_LIST = [
#    u'.'.join((key, value)) for key, value_list in OBSERVED_FIELDS.items()
#    for value in value_list]

AUTHORS_TOP_LIMIT = getattr(settings, 'AUTHORS_TOP_LIMIT', 10)

TIMELINE_FEED_DAYS = getattr(settings, 'TIMELINE_FEED_DAYS', 3)
