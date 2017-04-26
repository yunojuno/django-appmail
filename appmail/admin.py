# -*- coding: utf-8 -*-
from django.contrib.admin import site, ModelAdmin, SimpleListFilter
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .compat import reverse
from .models import EmailTemplate


class ValidTemplateListFilter(SimpleListFilter):

    """Filter on whether the template can be rendered or not."""

    title = _('Is valid')
    parameter_name = 'valid'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('1', _('True')),
            ('0', _('False')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        valid_ids = []
        invalid_ids = []
        for obj in queryset:
            try:
                obj.clean()
                valid_ids.append(obj.pk)
            except ValidationError:
                invalid_ids.append(obj.pk)

        if self.value() == '1':
            return queryset.filter(pk__in=valid_ids)
        if self.value() == '0':
            return queryset.filter(pk__in=invalid_ids)


class EmailTemplateAdmin(ModelAdmin):

    list_display = (
        'name',
        'subject',
        'language',
        'version',
        'is_valid'
    )

    list_filter = (
        'language',
        'version',
        ValidTemplateListFilter
    )

    readonly_fields = (
        'render_subject',
        'render_text',
        'render_html',
    )

    search_fields = (
        'name',
        'subject'
    )

    def _iframe(self, url):
        return (
            "<iframe class='appmail' src='{}' onload='resizeIframe(this)'></iframe><br/>"
            "<a href='{}' target='_blank'>View in new tab.</a>"
            .format(url, url)
        )

    def is_valid(self, obj):
        """Return True if the template can be rendered."""
        try:
            obj.clean()
            return True
        except ValidationError:
            return False
    is_valid.boolean = True

    def render_subject(self, obj):
        if obj.id is None:
            url = ''
        else:
            url = reverse(
                'appmail:render_template_subject',
                kwargs={'template_id': obj.id}
            )
        return self._iframe(url)
    render_subject.short_description = 'Rendered subject'
    render_subject.allow_tags = True

    def render_text(self, obj):
        if obj.id is None:
            url = ''
        else:
            url = reverse(
                'appmail:render_template_body_text',
                kwargs={'template_id': obj.id}
            )
        return self._iframe(url)
    render_text.short_description = 'Rendered body (plain)'
    render_text.allow_tags = True

    def render_html(self, obj):
        if obj.id is None:
            url = ''
        else:
            url = reverse(
                'appmail:render_template_body_html',
                kwargs={'template_id': obj.id}
            )
        return self._iframe(url)
    render_html.short_description = 'Rendered body (html)'
    render_html.allow_tags = True


site.register(EmailTemplate, EmailTemplateAdmin)
