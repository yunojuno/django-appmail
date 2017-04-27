# -*- coding: utf-8 -*-
from django import forms
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _

from .models import EmailTemplate


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
        label=_("To"),
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
