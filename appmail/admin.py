# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib import messages
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from .compat import reverse
from .forms import JSONWidget
from .models import EmailTemplate


class ValidTemplateListFilter(admin.SimpleListFilter):

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


class EmailTemplateAdmin(admin.ModelAdmin):

    formfield_overrides = {
        JSONField: {'widget': JSONWidget},
    }

    list_display = (
        'name',
        'subject',
        'language',
        'version',
        'has_text',
        'has_html',
        'is_valid',
        'is_active'
    )

    list_filter = (
        'language',
        'version',
        ValidTemplateListFilter,
        'is_active'
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
    actions = (
        'clone_templates',
        'send_test_emails',
    )
    fieldsets = (
        (
            'Basic Information',
            {
                'fields': (
                    'name',
                    'description',
                    'language',
                    'version',
                )
            }
        ),
        (
            'Templates',
            {
                'fields': (
                    'subject',
                    'body_text',
                    'body_html',
                )
            }
        ),
        (
            'Sample Output',
            {
                'fields': (
                    'test_context',
                    'render_subject',
                    'render_text',
                    'render_html',
                )
            }
        )
    )

    def _iframe(self, url):
        return (
            "<iframe class='appmail' src='{}' onload='resizeIframe(this)'></iframe><br/>"
            "<a href='{}' target='_blank'>View in new tab.</a>"
            .format(url, url)
        )

    # these functions are here rather than on the model so that we can get the
    # boolean icon.
    def has_text(self, obj):
        return len(obj.body_text or '') > 0
    has_text.boolean = True

    def has_html(self, obj):
        return len(obj.body_html or '') > 0
    has_html.boolean = True

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

    def send_test_emails(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        url = '{}?templates={}'.format(
            reverse('appmail:send_test_email'),
            ','.join(selected)
        )
        return HttpResponseRedirect(url)
    send_test_emails.short_description = _("Send test email for selected templates")

    def clone_templates(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        templates = EmailTemplate.objects.filter(pk__in=selected)
        for template in templates:
            template.clone()
            messages.success(request, _("Cloned template '%s'" % template.name))
        return HttpResponseRedirect(request.path)
    clone_templates.short_description = _("Clone selected email templates")


admin.site.register(EmailTemplate, EmailTemplateAdmin)
