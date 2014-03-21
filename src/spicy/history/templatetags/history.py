from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
@stringfilter
def colorize_diff(value):
    """
    Colorize diff like hgweb does ;-)
    """
    return mark_safe(
        u'\n'.join(
            '<span%s>%s</span>' % (
                (' style="color:#cc0000;"' if line.startswith('-') else
                 (' style="color:#008800;"' if line.startswith('+') else
                  (' style="color:#990099;"' if line.startswith('@') else
                   ''))),
                conditional_escape(line)) for line in value.splitlines()))
