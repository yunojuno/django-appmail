# -*- coding: utf-8 -*-
import json
import logging

from django import forms
from django.contrib import messages
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from .models import EmailTemplate

logger = logging.getLogger(__name__)


class MultiEmailField(forms.Field):

    """Taken from https://docs.djangoproject.com/en/1.11/ref/forms/validation/#form-field-default-cleaning """  # noqa

    def to_python(self, value):
        """Normalize data to a list of strings."""
        # Return an empty list if no input was given.
        if not value:
            return []
        return value.split(',')

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
        if not value:
            return EmailTemplate.objects.none()
        return EmailTemplate.objects.filter(pk__in=value.split(','))


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
        try:
            return json.loads(self.cleaned_data['context'])
        except ValueError as ex:
            raise forms.ValidationError(_("Invalid JSON: %s" % ex))

    def send_emails(self, request):
        """Send test emails."""
        for template in self.cleaned_data.get('templates'):
            email = template.create_message(
                self.cleaned_data['context'],
                from_email=self.cleaned_data['from_email'],
                to=self.cleaned_data['to'],
                cc=self.cleaned_data['cc'],
                bcc=self.cleaned_data['bcc']
            )
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
