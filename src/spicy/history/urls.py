from django.conf.urls import patterns, url, include


admin_urls = patterns(
    'spicy.history.admin',
    url(r'^$', 'actions_list', name='index'),
    url(r'^actions/(?P<action_id>\d+)/$', 'view_action', name='action'),
    url(r'^diffs/(?P<diff_id>\d+)/$', 'view_diff', name='diff'),
)

urlpatterns = patterns(
    '',
    url(r'^admin/history/', include(admin_urls, namespace='admin')),
#    url(r'^', include(public_urls, namespace='public')),
)
