from django import forms
from django.utils.translation import ugettext_lazy as _
from spicy.core.profile import defaults as pr_defaults
from spicy.utils import get_custom_model_class

Profile = get_custom_model_class(pr_defaults.CUSTOM_USER_MODEL)


class ActionsFilterForm(forms.Form):
    profile = forms.ModelChoiceField(
        label=_('User'), queryset=Profile.objects.all())
    ip = forms.CharField(
        label=_('IP address'), max_length=15,
        help_text=_('Add * to IP address to match subnetworks, i.e. 127.0.*'))
    filter_from = forms.DateTimeField(
        label=_('From date'),
        widget=forms.DateTimeInput(
            attrs={'class': 'datetime fill-up'}, format='%Y-%m-%d %H:%M'))
    filter_to = forms.DateTimeField(
        label=_('To date'),
        widget=forms.DateTimeInput(
            attrs={'class': 'datetime fill-up'}, format='%Y-%m-%d %H:%M'))
