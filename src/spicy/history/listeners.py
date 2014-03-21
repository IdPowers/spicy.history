import datetime
import difflib
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from spicy.core.service import api
from spicy.core.siteskin.threadlocals import get_current_ip, get_current_user
from . import defaults, utils


@transaction.commit_on_success
def object_post_save(sender, **kwargs):
    sender_name = '.'.join((sender._meta.app_label, sender._meta.object_name))
    
    from . import models
    instance = kwargs.get('instance')

    consumer_type = ContentType.objects.get_for_model(sender)
    action_type = getattr(
        instance, '_action_type',
        defaults.ACTION_CREATE if kwargs.get('created') else
        defaults.ACTION_EDIT)

    if action_type == defaults.ACTION_ROLLBACK:
        return

    timeline_observed = utils.is_observed(sender_name, action_type)
    if not ((sender_name in defaults.OBSERVED_FIELDS) or
            timeline_observed):
        return

    profile = get_current_user()
    if profile and profile.is_anonymous():
        profile = None

    if action_type == defaults.ACTION_EDIT:
        today = datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)
        if models.Action.objects.filter(
                consumer_type=consumer_type, consumer_id=instance.pk,
                action_type__in=(defaults.ACTION_CREATE, defaults.ACTION_EDIT),
                date_joined__gte=today).exists():
            instance._ignore_in_timeline = True
    provider = models.Action.objects.create(
        consumer_type=consumer_type, consumer_id=instance.pk,
        action_type=action_type, profile=profile, ip=get_current_ip(),
        show_in_timeline=not getattr(instance, '_ignore_in_timeline', False))

    if action_type == defaults.ACTION_CREATE:
        instance._ignore_in_timeline = True
        return

    fields = (
        set(defaults.OBSERVED_FIELDS.get(sender_name, ())) |
        set(defaults.TIMELINE_FIELDS.get(sender_name, ())
            if timeline_observed else ()))
    if fields:
        consumer_name = unicode(provider.consumer).encode('utf-8')

    diff = None
            
    for field in fields:
        last_version = api.register['history'].get_last_version(
            sender._meta.module_name, instance.pk, field)
        if last_version > 0:
            diffs = models.Diff.objects.filter(
                action__consumer_type=consumer_type,
                action__consumer_id=instance.pk, field=field,
                version=last_version)
            if len(diffs) > 1:
                for diff in diffs[1:]:
                    diff.delete()
            last_diff = diffs[0]
            last_value = last_diff.get_version_text().encode('utf-8')
        else:
            last_value = ''
        new_value = utils.to_unicode(getattr(instance, field)).encode('utf-8')

        if last_value != new_value:
            try:
                last_action = models.Action.objects.filter(
                    diff__version=last_version, diff__field=field,
                    consumer_type__model=sender._meta.module_name,
                    consumer_id=instance.pk)[0]
                last_date = last_action.date_joined
            except IndexError:
                last_date = ''
                last_value = ''
             
            patch = '\n'.join(difflib.unified_diff(
                last_value.splitlines(), new_value.splitlines(),
                consumer_name, consumer_name, last_date,
                str(provider.date_joined), lineterm=''))

            new_version = last_version + 1
            diff = models.Diff.objects.create(
                action=provider, version=new_version, field=field,
                change=patch)

            # Make sure that we can get latest version without errors.
            diff = models.Diff.objects.get(
                action__consumer_type=consumer_type,
                action__consumer_id=instance.pk, field=field,
                version=new_version)
            diff.get_version_text()
    if not diff:
        provider.delete()


def object_pre_delete(sender, **kwargs):
    sender_name = '.'.join((sender._meta.app_label, sender._meta.object_name))
    if (
            (sender_name in defaults.OBSERVED_FIELDS) or
            utils.is_observed(sender_name, defaults.ACTION_DELETE)):
        from . import models
        instance = kwargs.get('instance')
        models.Action.objects.create(
            consumer_type=ContentType.objects.get_for_model(sender),
            consumer_id=instance.pk, action_type=defaults.ACTION_DELETE,
            profile=get_current_user(), ip=get_current_ip())
