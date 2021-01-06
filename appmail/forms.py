from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Union

from django import forms
from django.contrib import messages
from django.core.validators import validate_email
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _lazy

from .models import AppmailMessage, EmailTemplate, EmailTemplateQuerySet

logger = logging.getLogger(__name__)


class JSONWidget(forms.Textarea):
    """Pretty print JSON in a text area."""

    DEFAULT_ATTRS = {
        "class": "vLargeTextField",
        "rows": 15,
    }  # type: Dict[str, Union[str, int]]

    def format_value(self, value: str) -> str:
        """Pretty format JSON text."""
        value = value or "{}"
        if not isinstance(value, str):
            raise TypeError("Value must JSON parseable string instance")
        value = json.loads(value)
        return json.dumps(value, indent=4, sort_keys=True)

    def render(
        self,
        name: str,
        value: str,
        attrs: Optional[Dict[str, Union[str, int]]] = None,
        renderer: Optional[forms.renderers.BaseRenderer] = None,
    ) -> str:
        attrs = attrs or JSONWidget.DEFAULT_ATTRS
        value = self.format_value(value)
        return super().render(name, value, attrs=attrs, renderer=renderer)


class MultiEmailField(forms.Field):
    """Taken from https://docs.djangoproject.com/en/1.11/ref/forms/validation/#form-field-default-cleaning """  # noqa

    def to_python(self, value: Optional[Union[List[str], str]]) -> List[str]:
        """Normalize data to a list of strings."""
        if isinstance(value, list):
            return value

        if not value:
            return []

        return [v.strip() for v in value.split(",")]

    def validate(self, value: List[str]) -> None:
        """Check if value consists only of valid emails."""
        # Use the parent's handling of required fields, etc.
        super().validate(value)
        for email in value:
            validate_email(email)


class MultiEmailTemplateField(forms.Field):
    """Convert comma-separated ids into EmailTemplate queryset."""

    def to_python(
        self, value: Optional[Union[EmailTemplateQuerySet, str]]
    ) -> EmailTemplateQuerySet:
        """Normalize data to a queryset of EmailTemplates."""
        if isinstance(value, EmailTemplateQuerySet):
            return value

        if not value:
            return EmailTemplate.objects.none()

        values = [int(i) for i in value.split(",")]
        return EmailTemplate.objects.filter(pk__in=values)


class EmailTestForm(forms.Form):
    """Renders email template on intermediate page."""

    from_email = forms.EmailField(
        label=_lazy("From"), help_text=_lazy("Email address to be used as the sender")
    )
    reply_to = MultiEmailField(
        label=_lazy("Reply-To"),
        help_text=_lazy("Comma separated list of email addresses"),
    )
    to = MultiEmailField(
        label=_lazy("To"), help_text=_lazy("Comma separated list of email addresses")
    )
    cc = MultiEmailField(
        label=_lazy("cc"),
        help_text=_lazy("Comma separated list of email addresses"),
        required=False,
    )
    bcc = MultiEmailField(
        label=_lazy("bcc"),
        help_text=_lazy("Comma separated list of email addresses"),
        required=False,
    )
    context = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text=_lazy("JSON used to render the subject and body templates"),
    )
    # comma separated list of template ids.
    templates = MultiEmailTemplateField(widget=forms.HiddenInput())

    def clean_context(self) -> dict:
        """Load text input back into JSON."""
        context = self.cleaned_data["context"] or "{}"
        try:
            return json.loads(context)
        except (TypeError, ValueError) as ex:
            raise forms.ValidationError(_lazy("Invalid JSON: %s" % ex))

    def _create_message(self, template: EmailTemplate) -> AppmailMessage:
        """Create EmailMultiMessage from form data."""
        return AppmailMessage(
            template,
            self.cleaned_data["context"],
            from_email=self.cleaned_data["from_email"],
            to=self.cleaned_data["to"],
            cc=self.cleaned_data["cc"],
            bcc=self.cleaned_data["bcc"],
        )

    def send_emails(self, request: HttpRequest) -> None:
        """Send test emails."""
        for template in self.cleaned_data.get("templates"):
            email = self._create_message(template)
            try:
                email.send()
            except Exception as ex:  # pylint: disable=broad-except
                logger.exception("Error sending test email")
                messages.error(
                    request,
                    _lazy("Error sending test email '%s': %s" % (template.name, ex)),
                )
            else:
                messages.success(
                    request,
                    _lazy(
                        "'%s' email sent to '%s'" % (template.name, ", ".join(email.to))
                    ),
                )
