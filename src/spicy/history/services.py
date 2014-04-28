import difflib
import operator
from collections import defaultdict
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count
from django.db.models.fields import related
from django.http import Http404
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _
from functools import reduce
from spicy.core.admin import defaults as admin_defaults
from spicy.core.profile.decorators import is_staff
from spicy.core.service import api
from spicy.core.siteskin.decorators import ajax_request, render_to
from spicy.utils import NavigationFilter
from . import models, defaults, utils


class HistoryProvider(api.Provider):
    model = 'history.Action'

    @is_staff(required_perms='history.view_history')
    @render_to(
        'services/list.html',
        url_pattern='/(?P<consumer_type>\w+)/(?P<consumer_id>\d+)/$',
        use_admin=True)
    def list(self, request, consumer_type, consumer_id):
        ctype = ContentType.objects.get(model=consumer_type)
        consumer_model = ctype.model_class()
        consumer = consumer_model.objects.get(pk=consumer_id)
        search_query = Q(
            consumer_type__model=consumer_type) & Q(
            consumer_id=consumer_id)
        nav = NavigationFilter(request)
        paginator_base_url = '.'
        paginator = nav.get_queryset_with_paginator(
            self.model, paginator_base_url,
            obj_per_page=admin_defaults.ADMIN_OBJECTS_PER_PAGE,
            search_query=search_query)
        objects_list = paginator.current_page.object_list

        return {
            'nav': nav, 'objects_list': objects_list, 'paginator': paginator,
            'consumer': consumer, 'consumer_type_id': ctype.id,
            'fields': defaults.OBSERVED_FIELDS.get(
                '.'.join((
                    consumer_model._meta.app_label,
                    consumer_model._meta.object_name)))}

    @is_staff(required_perms='history.view_history')
    @render_to(
        'services/list.html', use_admin=True,
        url_pattern=(
            '/(?P<consumer_type>\w+)/(?P<consumer_id>\d+)/(?P<field>\w+)/$'))
    def list_by_field(self, request, consumer_type, consumer_id, field):
        ctype = ContentType.objects.get(model=consumer_type)
        consumer_model = ctype.model_class()
        consumer = consumer_model.objects.get(pk=consumer_id)
        provs = self.model.objects.filter(
            consumer_type__model=consumer_type,
            consumer_id=consumer_id, diff__field=field)
        return dict(provs=provs, consumer=consumer)

    @is_staff(required_perms='history.rollback')
    @ajax_request('/(?P<diff_id>[\d]+)/rollback/$')
    def rollback(self, request, diff_id):
        status = 'ok'
        message = ''

        diff = models.Diff.objects.get(pk=diff_id)
        action = models.Action.objects.create(
            action_type=defaults.ACTION_ROLLBACK,
            consumer_type_id=diff.action.consumer_type_id,
            consumer_id=diff.action.consumer_id,
            profile=request.user, rollback_to=diff,
            ip=request.META.get('REMOTE_ADDR'))

        last_diff = diff.last_version
        last_date = last_diff.action.date_joined
        last_value = utils.to_unicode(
            getattr(diff.action.consumer, diff.field))
        new_value = diff.get_version_text()

        if new_value == last_value:
            return {
                'status': 'error',
                'message': unicode(_('Old version matches current version'))}

        consumer_name = unicode(action.consumer).encode('utf-8')
        diff_text = '\n'.join(difflib.unified_diff(
            last_value.encode('utf-8').splitlines(),
            new_value.encode('utf-8').splitlines(),
            consumer_name, consumer_name, last_date,
            unicode(action.date_joined).encode('utf-8'), lineterm=''))
        models.Diff.objects.create(
            action=action, version=last_diff.version + 1,
            change=diff_text, field=diff.field)
        model = action.consumer_type.model_class()
        field = diff.field
        model_field = getattr(model, field, None)
        if model_field:
            if callable(model_field):
                raise ValueError("Unable to convert to a function")
            elif isinstance(
                    model_field, related.ReverseSingleRelatedObjectDescriptor):
                to_type = model_field.field.rel.to
            else:
                to_type = unicode
        else:
            to_type = getattr(action.consumer, diff.field).__class__

        setattr(
            action.consumer, field, utils.from_unicode(new_value, to_type))
        action.consumer._action_type = defaults.ACTION_ROLLBACK
        action.consumer.save()
        return dict(
            status=status, message=message,
            next_url=reverse(
                'history:admin:action', args=[action.pk]))

    @render_to(
        'history/authors_top.html', url_pattern='$', is_public=True)
    def authors_top(self, request):
        return {
            'authors': models.Profile.objects.annotate(
                Count('action')
            ).order_by('-action__count')[:defaults.AUTHORS_TOP_LIMIT]}

    @render_to('actions.html', use_admin=True)
    def __call__(self, request, consumer_type, consumer_id):
        ctype = ContentType.objects.get(model=consumer_type)
        consumer_model = ctype.model_class()
        consumer = consumer_model.objects.get(pk=consumer_id)
        objects_list = self.model.objects.filter(
            consumer_type__model=consumer_type,
            consumer_id=consumer_id)

        ids = self.model.objects.filter(
            profile__isnull=False, consumer_type__model=consumer_type,
            consumer_id=consumer_id).values_list('profile', flat=True)

        editors = api.register['profile'].get_profiles(id__in=ids)

        return {
            'editors': editors, 'consumer_type': consumer_type,
            'consumer_id': consumer_id,
            'objects_list': objects_list,
            'consumer': consumer, 'consumer_type_id': ctype.id,
            'fields': defaults.OBSERVED_FIELDS.get(
                '.'.join((
                    consumer_model._meta.app_label,
                    consumer_model._meta.object_name)))}

    @render_to(
        'spicy.history/rubric_timeline.html',
        url_pattern=(
            '/(?P<consumer_types>\w+(,\w+)?)/(?P<attr_name>\w+?)/'
            '(?P<attr_id>\d+)$'),
        use_siteskin=True, is_public=True)
    def attr_timeline(
            self, request, consumer_types='', attr_name='', attr_id=''):
        root = ''
        return self._timeline(
            request, consumer_types, root, attr_name=attr_name,
            attr_id=attr_id)

    @render_to(
        'spicy.history/rubric_timeline.html',
        url_pattern='/(?P<consumer_types>\w+(,\w+)?)/(?P<root>\S+)$',
        use_siteskin=True, is_public=True)
    def timeline(self, request, consumer_types='', root=''):
        return self._timeline(request, consumer_types, root)

    def _timeline(
            self, request, consumer_types, root, attr_name=None, attr_id=None):
        # Templates are cached in a dict.
        templates = defaultdict(
            lambda: get_template(
                'spicy.history/providers/%s.html' % template_name))

        # TODO custom SQL for consumer.root checking
        consumer_types_list = consumer_types.split(',')
        actions = models.Action.objects.filter(
            show_in_timeline=True,
            consumer_type__model__in=consumer_types_list,
            action_type__in=[0, 1],
            ).order_by('-date_joined')

        if attr_name is not None and attr_id is not None:
            queries = []
            action_ids = []
            for ctype_string in consumer_types_list:
                ctype = ContentType.objects.get(model=ctype_string)
                consumers = getattr(ctype.model_class(), 'objects').all()
                
                action_ids.extend(actions.filter(
                    consumer_type__id=ctype.id,
                    consumer_id__in=consumers.filter(
                        is_public=True,
                        **{attr_name: attr_id}).values_list('id', flat=True)
                    ).values_list('id', flat=True))
                            
            actions = actions.filter(
                pk__in=[aid for aid in action_ids])

        elif len(consumer_types_list) == 1:
            manager = (
                'with_attrs' if consumer_types == 'tag' else 'objects')
            ctype = ContentType.objects.get(model=consumer_types)
            consumers = getattr(ctype.model_class(), manager).all()
            if root:
                queries = []
                key = 'term__slug'
                for i in xrange(defaults.GEOTARGET_TAG_ROOT_DEPTH):
                    key = 'vocabulary__' + key
                    queries.append(Q(**{key: root}))
                consumers = consumers.filter(
                    reduce(operator.or_, queries), is_public=True)

            actions = actions.filter(
                consumer_id__in=[consumer.id for consumer in consumers])
            consumers_dict = dict(
                (consumer.id, consumer) for consumer in consumers)
            for action in actions:
                action.consumer = consumers_dict[action.consumer_id]
        
        providers = []
        for action in actions:
            if action.consumer and action.consumer.check_public():
                if root and hasattr(action.consumer, 'root'):
                    if action.consumer.root is None or (
                            action.consumer.root and
                            action.consumer.root.slug != root):
                        continue

                template_name = action.consumer.get_history_template(
                    action.action_type)
                context = Context({
                    'action': action, 'consumer': action.consumer})
                template = templates[template_name]
                action.rendered_template = template.render(context)
                providers.append(action)

        page = request.GET.get('page', 1)
        paginator = Paginator(providers, sk_defaults.OBJECTS_PER_PAGE)

        try:
            paginator.current_page = paginator.page(page)
        except InvalidPage:
            raise Http404(unicode(_('Page %s does not exist.' % page)))
        #paginator.base_url = reverse(
        #     'service:public:history-timeline', args=[consumer_types, root])

        return dict(
            paginator=paginator, consumer_types=consumer_types, root=root)


class HistoryService(api.Interface):
    name = 'history'
    label = _('History service')

    PROVIDER_TEMPLATES_DIR = 'spicy.history/providers/'

    schema = dict(GENERIC_CONSUMER=HistoryProvider)

    def get_last_version(self, consumer_type, consumer_id, field):
        try:
            return models.Diff.objects.filter(
                action__consumer_type__model=consumer_type,
                action__consumer_id=consumer_id, field=field
                ).order_by('-version')[0].version
        except IndexError:
            return 0
