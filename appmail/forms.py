# -*- coding: utf-8 -*-
import json
import logging
from six import string_types

from django import forms
from django.contrib import messages
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from .models import EmailTemplate, EmailTemplateQuerySet

logger = logging.getLogger(__name__)


class JSONWidget(forms.Textarea):

    """Pretty print JSON in a text area."""

    DEFAULT_ATTRS = {'class': 'vLargeTextField', 'rows': 15}

    def format_value(self, value):
        """Pretty format JSON text."""
        value = value or '{}'
        assert isinstance(value, string_types), _("Invalid JSON text input type")
        value = json.loads(value)
        return json.dumps(value, indent=4, sort_keys=True)

    def render(self, name, value, attrs=DEFAULT_ATTRS):
        value = self.format_value(value)
        return super(JSONWidget, self).render(name, value, attrs=attrs)


class MultiEmailField(forms.Field):

    """Taken from https://docs.djangoproject.com/en/1.11/ref/forms/validation/#form-field-default-cleaning """  # noqa

    def to_python(self, value):
        """Normalize data to a list of strings."""
        if isinstance(value, list):
            return value

        if not value:
            return []

        return [v.strip() for v in value.split(',')]

    def validate(self, value):
        """Check if value consists only of valid emails."""
        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)
        for email in value:
            validate_email(email)


class MultiEmailTemplateField(forms.Field):

    """Convert comma-separated ids into EmailTemplate queryset."""

    def to_python(self, value):
        """Normalize data to a queryset of EmailTemplates."""
        if isinstance(value, EmailTemplateQuerySet):
            return value

        if not value:
            return EmailTemplate.objects.none()

        values = [int(i) for i in value.split(',')]
        return EmailTemplate.objects.filter(pk__in=values)


class EmailTestForm(forms.Form):

    """Renders email template on intermediate page."""

    from_email = forms.EmailField(
        label=_("From"),
        help_text=_("Email address to be used as the sender")
    )
    to = MultiEmailField(
        label=_("To"),
        help_text=_("Comma separated list of email addresses")
    )
    cc = MultiEmailField(
        label=_("cc"),
        help_text=_("Comma separated list of email addresses"),
        required=False
    )
    bcc = MultiEmailField(
        label=_("bcc"),
        help_text=_("Comma separated list of email addresses"),
        required=False
    )
    context = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_("JSON used to render the subject and body templates")
    )
    # comma separated list of template ids.
    templates = MultiEmailTemplateField(
        widget=forms.HiddenInput()
    )

    def clean_context(self):
        """Load text input back into JSON."""
        context = self.cleaned_data['context'] or '{}'
        try:
            return json.loads(context)
        except (TypeError, ValueError) as ex:
            raise forms.ValidationError(_("Invalid JSON: %s" % ex))

    def _create_message(self, template):
        """Create EmailMultiMessage from form data."""
        return template.create_message(
            self.cleaned_data['context'],
            from_email=self.cleaned_data['from_email'],
            to=self.cleaned_data['to'],
            cc=self.cleaned_data['cc'],
            bcc=self.cleaned_data['bcc']
        )

    def send_emails(self, request):
        """Send test emails."""
        for template in self.cleaned_data.get('templates'):
            email = self._create_message(template)
            try:
                email.send()
            except Exception as ex:
                logger.exception("Error sending test email")
                messages.error(
                    request,
                    _("Error sending test email '%s': %s" % (template.name, ex))
                )
            else:
                messages.success(
                    request,
                    _("'%s' email sent to '%s'" % (template.name, ', '.join(email.to)))
                )
