from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from spicy.core.admin import defaults as admin_defaults
from spicy.core.admin.conf import AdminAppBase, AdminLink, Perms
from spicy.core.profile.decorators import is_staff
from spicy.core.siteskin.decorators import render_to
from spicy.utils import NavigationFilter
from . import forms, models


class AdminApp(AdminAppBase):
    name = 'history'
    label = _('History log')
    order_number = 110

    menu_items = (
        AdminLink('history:admin:index', _('View history log')),
    )

    perms = Perms(view=[],  write=[], manage=[])

    @render_to('menu.html', use_admin=True)
    def menu(self, request, *args, **kwargs):
        return dict(app=self, *args, **kwargs)

    @render_to('dashboard.html', use_admin=True)
    def dashboard(self, request, *args, **kwargs):
        return dict(app=self, *args, **kwargs)


@is_staff(required_perms='history.view_history')
@render_to('list.html', use_admin=True)
def actions_list(request):
    filters = (
        ('profile', None), ('ip', ''), ('filter_from', ''), ('filter_to', ''))
    nav = NavigationFilter(request, accepting_filters=filters)
    form = forms.ActionsFilterForm(request.GET)

    search_query = Q()
    if nav.profile:
        search_query &= Q(profile=nav.profile)
    if nav.ip:
        if nav.ip.endswith('*'):
            search_query &= Q(ip__startswith=nav.ip[:-1])
        else:
            search_query &= Q(ip=nav.ip)
    if nav.filter_from:
        search_query &= Q(date_joined__gte=nav.filter_from)
    if nav.filter_to:
        search_query &= Q(date_joined__lte=nav.filter_to)

    paginator = nav.get_queryset_with_paginator(
        models.Action, reverse('history:admin:index'),
        search_query=([search_query], {}),
        obj_per_page=admin_defaults.ADMIN_OBJECTS_PER_PAGE
        )

    return {
        'objects_list': paginator.current_page.object_list,
        'paginator': paginator, 'nav': nav, 'form': form,
        'edit_url': 'history:admin:action'}


@is_staff(required_perms='history.view_history')
@render_to('action.html', use_admin=True)
def view_action(request, action_id):
    action = models.Action.objects.get(pk=action_id)
    return {'action': action}


@is_staff(required_perms='history.view_history')
@render_to('diff.html', use_admin=True)
def view_diff(request, diff_id):
    diff = models.Diff.objects.get(pk=diff_id)
    return {'diff': diff}
