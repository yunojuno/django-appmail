# -*- coding: utf-8 -*-
import json

from django import forms
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from .models import EmailTemplate
from .settings import DEFAULT_SENDER


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


class MultiEmailTestForm(forms.Form):

    """Renders email templates on confirmation page."""

    to = MultiEmailField(
        label=_("Recipients"),
        help_text=_("Comma-sparated list of email addresses")
    )
    # comma separated list of template ids.
    templates = MultiEmailTemplateField(
        widget=forms.HiddenInput()
    )

    def emails(self):
        """EmailMultiPart objects from templates and form data."""
        for template in self.cleaned_data.get('templates'):
            email = template.create_message(
                template.body_html_context,
                to=self.cleaned_data.get('to'),
            )
            yield template, email


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

    def __init__(self, template, *args, **kwargs):
        self.template = template
        super(EmailTestForm, self).__init__(*args, **kwargs)
        self.fields['from_email'].initial = DEFAULT_SENDER
        self.fields['context'].initial = json.dumps(
            self.template.placeholder_context(),
            indent=4,
            sort_keys=True
        )

    def clean_context(self):
        """Load text input back into JSON."""
        try:
            return json.loads(self.cleaned_data['context'])
        except ValueError as ex:
            raise forms.ValidationError(_("Invalid JSON: %s" % ex))

    def email(self):
        """Return EmailMultiMessage object from template and form data."""
        return self.template.create_message(
            self.cleaned_data['context'],
            from_email=self.cleaned_data['from_email'],
            to=self.cleaned_data['to'],
            cc=self.cleaned_data['cc'],
            bcc=self.cleaned_data['bcc'],
        )
