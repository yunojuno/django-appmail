# -*- coding: utf-8 -*-
from django.contrib.admin import site, ModelAdmin
from django.urls import reverse

from .models import EmailTemplate


class EmailTemplateAdmin(ModelAdmin):

    list_display = (
        'name',
        'subject',
        'language',
        'version',
    )

    list_filter = (
        'name',
        'language',
        'version'
    )

    readonly_fields = (
        'render_subject',
        'render_text',
        'render_html',
    )

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

    def _iframe(self, url):
        return (
            "<iframe class='appmail' src='{}' onload='resizeIframe(this)'></iframe><br/>"
            "<a href='{}' target='_blank'>View in new tab (test with variables).</a>"
            .format(url, url)
        )

    def _url(self, obj, format):
        if obj.id is None:
            return ''
        url = reverse(
            'appmail:render_template_body',
            kwargs={'template_id': obj.id}
        )
        return "{}?format={}".format(url, format)

    def render_text(self, obj):
        return self._iframe(self._url(obj, 'plain'))
    render_text.short_description = 'Rendered body (plain)'
    render_text.allow_tags = True

    def render_html(self, obj):
        return self._iframe(self._url(obj, 'html'))
    render_html.short_description = 'Rendered body (html)'
    render_html.allow_tags = True


site.register(EmailTemplate, EmailTemplateAdmin)
