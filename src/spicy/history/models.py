from django.db import models
from django.utils.translation import ugettext_lazy as _
from spicy.core.service import models as service_models
from spicy.core.profile.defaults import CUSTOM_USER_MODEL
from spicy.utils import cached_property
from . import defaults, utils, listeners


class Action(service_models.ProviderModel):
    action_type = models.PositiveSmallIntegerField(
        _('Action type'), choices=defaults.ACTION_TYPES)
    profile = models.ForeignKey(
        CUSTOM_USER_MODEL, null=True, verbose_name=_('User'))
    rollback_to = models.ForeignKey(
        'Diff', null=True, related_name='rolled_back_from',
        verbose_name=_('Rollback to'))
    ip = models.CharField(_('IP address'), max_length=15, null=True)
    show_in_timeline = models.BooleanField(
        _('Show in timeline'), default=True)
    # show_in_timeline doesn't guarantee that this action goes to timeline,
    # so it'll be set to False only if we know that this action happened today.

    def is_rollback(self):
        return self.action_type == defaults.ACTION_ROLLBACK

    def consumer_model_verbose(self):
        return self.consumer_type.model_class()._meta.verbose_name

    @models.permalink
    def get_absolute_url(self):
        if self.action_type != defaults.ACTION_DELETE:
            return 'history:admin:view-action', (self.pk,),

    def __unicode__(self):
        return u'%s %s' % (
            self.get_action_type_display(), self.consumer)

    class Meta:
        ordering = ['-date_joined']
        db_table = 'hs_action'
        permissions = (
            ('rollback', 'Rollback history'),
            ('view_history', 'View history'),
        )


class Diff(models.Model):
    action = models.ForeignKey(Action)
    version = models.PositiveIntegerField()
    change = models.TextField()
    field = models.CharField(
        max_length=255,
        choices=[(field, field) for field in defaults.OBSERVED_FIELD_NAMES])

    @cached_property
    def first_version(self):
        try:
            return Diff.objects.select_related('action').order_by(
                'version').get(
                    action__consumer_type__id=self.action.consumer_type_id,
                    action__consumer_id=self.action.consumer_id,
                    field=self.field, version=1)
        except Diff.DoesNotExist:
            pass
        
    @cached_property
    def prev_version(self):
        try:
            return Diff.objects.select_related('action').get(
                action__consumer_type__id=self.action.consumer_type_id,
                action__consumer_id=self.action.consumer_id,
                field=self.field, version=self.version-1)
        except Diff.DoesNotExist:
            pass
        
    @cached_property
    def next_version(self):
        try:
            return Diff.objects.select_related('action').get(
                action__consumer_type__id=self.action.consumer_type_id,
                action__consumer_id=self.action.consumer_id,
                field=self.field, version=self.version+1)
        except Diff.DoesNotExist:
            pass

    @cached_property
    def last_version(self):
        try:
            return Diff.objects.select_related('action').filter(
                action__consumer_type__id=self.action.consumer_type_id,
                action__consumer_id=self.action.consumer_id,
                field=self.field).order_by('-version')[0]
        except IndexError:
            pass

    def get_version_text(self):
        return utils.merge([
            value[0] for value in self.__class__.objects.filter(
                action__consumer_type__id=self.action.consumer_type_id,
                action__consumer_id=self.action.consumer_id, field=self.field,
                version__lte=self.version
                ).order_by('version').values_list('change', 'version')])

    def verbose_field_name(self):
        if self.field:
            model = self.action.consumer_type.model_class()
            name = getattr(
                getattr(
                    getattr(model, self.field, None), 'fget', None),
                'verbose_name', None)
            if not name:
                return unicode(model._meta.get_field_by_name(
                    self.field)[0].verbose_name.decode('utf-8'))
            return unicode(name.decode('utf-8'))

    @models.permalink
    def get_absolute_url(self):
        return 'history:admin:diff', (self.id,),

    def __unicode__(self):
        return u'{name}@{version}'.format(
            name=self.verbose_field_name(), version=self.version)

    class Meta:
        db_table = 'hs_diff'
        permissions = (
            ('rollback', 'Rollback to older version'),
        )
        unique_together = (
            ('action', 'field'),
        )

models.signals.post_save.connect(listeners.object_post_save)
models.signals.pre_delete.connect(listeners.object_pre_delete)
