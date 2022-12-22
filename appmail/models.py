from __future__ import annotations

from typing import Any, Callable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.http import HttpRequest
from django.template import Context, Template, TemplateDoesNotExist, TemplateSyntaxError
from django.urls import NoReverseMatch
from django.utils.timezone import now as tz_now
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from . import helpers
from .settings import (
    ADD_EXTRA_HEADERS,
    CONTEXT_PROCESSORS,
    LOG_SENT_EMAILS,
    VALIDATE_ON_SAVE,
)

User = get_user_model()


class EmailTemplateQuerySet(models.query.QuerySet):
    def active(self) -> EmailTemplateQuerySet:
        """Return active templates only."""
        return self.filter(is_active=True)

    def current(
        self, name: str, language: str = settings.LANGUAGE_CODE
    ) -> EmailTemplateQuerySet:
        """Return the latest version of a template."""
        return (
            self.active()
            .filter(name=name, language=language)
            .order_by("version")
            .last()
        )

    def version(
        self, name: str, version: str, language: str = settings.LANGUAGE_CODE
    ) -> EmailTemplate:
        """Return a specific version of a template."""
        return self.active().get(name=name, language=language, version=version)


class EmailTemplate(models.Model):
    """
    Email template. Contains HTML and plain text variants.

    Each Template object has a unique name:language.version combination, which
    means that localisation of templates is managed through having multiple
    objects with the same name - there is no inheritence model. This is to
    keep it simple:

        order-confirmation:en.0
        order-confirmation:de.0
        order-confirmation:fr.0

    Templates contain HTML and plain text content.

    """

    CONTENT_TYPE_PLAIN = "text/plain"
    CONTENT_TYPE_HTML = "text/html"
    CONTENT_TYPES = (CONTENT_TYPE_PLAIN, CONTENT_TYPE_HTML)

    name = models.CharField(
        _lazy("Template name"),
        max_length=100,
        help_text=_lazy(
            "Template name - must be unique for a given language/version combination."
        ),
        db_index=True,
    )
    description = models.CharField(
        _lazy("Description"),
        max_length=100,
        help_text=_lazy(
            "Optional description. e.g. used to differentiate variants ('new header')."
        ),  # noqa
        blank=True,
    )
    # language is free text and not a choices field as we make no assumption
    # as to how the end user is storing / managing languages.
    language = models.CharField(
        _lazy("Language"),
        max_length=20,
        default=settings.LANGUAGE_CODE,
        help_text=_lazy(
            "Used to support localisation of emails, defaults to "
            "`settings.LANGUAGE_CODE`, but can be any string, e.g. 'London', 'NYC'."
        ),
        db_index=True,
    )
    version = models.IntegerField(
        _lazy("Version (or variant)"),
        default=0,
        help_text=_lazy("Integer value - can be used for versioning or A/B testing."),
        db_index=True,
    )
    subject = models.CharField(
        _lazy("Subject line template"),
        max_length=100,
        help_text=_lazy("Email subject line (may contain template variables)."),
    )
    body_text = models.TextField(
        _lazy("Plain text template"),
        help_text=_lazy("Plain text content (may contain template variables)."),
    )
    body_html = models.TextField(
        _lazy("HTML template"),
        help_text=_lazy("HTML content (may contain template variables)."),
    )
    test_context = models.JSONField(
        default=dict,
        blank=True,
        help_text=_lazy(
            "Dummy JSON used for test rendering (set automatically on first save)."
        ),
    )
    is_active = models.BooleanField(
        _lazy("Active (live)"),
        help_text=_lazy("Set to False to remove from `current` queryset."),
        default=True,
    )
    from_email = models.CharField(
        _lazy("Sender"),
        max_length=254,
        help_text=_lazy(
            "Default sender address if none specified. Verbose form is accepted."
        ),
        default=settings.DEFAULT_FROM_EMAIL,
    )
    reply_to = models.CharField(
        _lazy("Reply-To"),
        max_length=254,
        help_text=_lazy("Comma separated list of Reply-To recipients."),
        default=settings.DEFAULT_FROM_EMAIL,
    )
    supports_attachments = models.BooleanField(
        _lazy("Supports attachments"),
        default=False,
        help_text=_lazy("Does this template support file attachments?"),
    )

    objects = EmailTemplateQuerySet().as_manager()

    class Meta:
        unique_together = ("name", "language", "version")

    def __str__(self) -> str:
        return f"{self.name} (language={self.language}; version={self.version})"

    def __repr__(self) -> str:
        return (
            f"<EmailTemplate id={self.id} name='{self.name}' "
            f"language='{self.language}' version={self.version}>"
        )

    @property
    def extra_headers(self) -> dict[str, str]:
        return {
            "X-Appmail-Template": (
                f"name={self.name}; language={self.language}; version={self.version}"
            )
        }

    @property
    def reply_to_list(self) -> list[str]:
        """Convert the reply_to field to a list."""
        return [a.strip() for a in self.reply_to.split(",")]

    def save(self, *args: Any, **kwargs: Any) -> EmailTemplate:
        """
        Update dummy context on first save and validate template contents.

        Kwargs:
            validate: set to False to bypass template validation; defaults
                to settings.VALIDATE_ON_SAVE.

        """
        if self.pk is None:
            self.test_context = helpers.get_context(
                self.subject + self.body_text + self.body_html
            )
        validate = kwargs.pop("validate", VALIDATE_ON_SAVE)
        if validate:
            self.clean()
        super(EmailTemplate, self).save(*args, **kwargs)
        return self

    def clean(self) -> None:
        """Validate model - specifically that the template can be rendered."""
        validation_errors = {}
        validation_errors.update(self._validate_body(EmailTemplate.CONTENT_TYPE_PLAIN))
        validation_errors.update(self._validate_body(EmailTemplate.CONTENT_TYPE_HTML))
        validation_errors.update(self._validate_subject())
        if validation_errors:
            raise ValidationError(validation_errors)

    def render_subject(
        self,
        context: dict,
        processors: list[Callable[[HttpRequest], dict]] = CONTEXT_PROCESSORS,
    ) -> str:
        """Render subject line."""
        ctx = Context(helpers.patch_context(context, processors), autoescape=False)
        return Template(self.subject).render(ctx)

    def _validate_subject(self) -> dict[str, str]:
        """Try rendering the body template and capture any errors."""
        try:
            self.render_subject({})
        except TemplateDoesNotExist as ex:
            return {"subject": _lazy("Template does not exist: {}".format(ex))}
        except TemplateSyntaxError as ex:
            return {"subject": str(ex)}
        else:
            return {}

    def render_body(
        self,
        context: dict,
        content_type: str = CONTENT_TYPE_PLAIN,
        processors: list[Callable[[HttpRequest], dict]] = CONTEXT_PROCESSORS,
    ) -> str:
        """Render email body in plain text or HTML format."""
        if content_type not in EmailTemplate.CONTENT_TYPES:
            raise ValueError(_(f"Invalid content type. Value supplied: {content_type}"))
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            ctx = Context(helpers.patch_context(context, processors), autoescape=False)
            return Template(self.body_text).render(ctx)
        if content_type == EmailTemplate.CONTENT_TYPE_HTML:
            ctx = Context(helpers.patch_context(context, processors))
            return Template(self.body_html).render(ctx)
        raise ValueError(f"Invalid content_type '{content_type}'.")

    def _validate_body(self, content_type: str) -> dict[str, str]:
        """Try rendering the body template and capture any errors."""
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            field_name = "body_text"
        elif content_type == EmailTemplate.CONTENT_TYPE_HTML:
            field_name = "body_html"
        else:
            raise ValueError("Invalid template content_type.")
        try:
            self.render_body({}, content_type=content_type)
        except TemplateDoesNotExist as ex:
            return {field_name: _("Template does not exist: {}".format(ex))}
        except (TemplateSyntaxError, NoReverseMatch) as ex:
            return {field_name: str(ex)}
        else:
            return {}

    def clone(self) -> EmailTemplate:
        """Create a copy of the current object, increase version by 1."""
        self.pk = None
        self.version += 1
        self.is_active = False
        return self.save()


class AppmailMessage(EmailMultiAlternatives):
    """
    Subclass EmailMultiAlternatives to be template-aware.

    This class behaves like a standard Django EmailMultiAlternatives
    email, but with the subject, body and 'text/html' alternative set
    from the template + context.

    The send method is overridden to enable the saving a copy of the
    message after it is sent.

    """

    def __init__(self, template: EmailTemplate, context: dict, **email_kwargs: Any):
        """
        Build AppmailMessage from template and context.

        The template and context are used to render the email subject line,
        body and HTML.

        The `email_kwargs` are passed direct to the EmailMultiAlternatives
        constructor - so can be anything that that supports (cc, bcc, etc.)

        """
        if "subject" in email_kwargs:
            raise ValueError(_("Invalid argument: 'subject' is set from the template."))
        if "body" in email_kwargs:
            raise ValueError(_("Invalid argument: 'body' is set from the template."))
        if "alternatives" in email_kwargs:
            raise ValueError(
                _("Invalid argument: 'alternatives' is set from the template.")
            )

        email_kwargs.setdefault("reply_to", template.reply_to_list)
        email_kwargs.setdefault("from_email", template.from_email)
        email_kwargs.setdefault("headers", {})
        if ADD_EXTRA_HEADERS:
            email_kwargs["headers"].update(template.extra_headers)

        if email_kwargs.get("attachments", None) and not template.supports_attachments:
            raise ValueError(_("Email template does not support attachments."))

        email_kwargs["subject"] = template.render_subject(context)
        email_kwargs["body"] = template.render_body(
            context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN
        )
        html = template.render_body(
            context, content_type=EmailTemplate.CONTENT_TYPE_HTML
        )
        email_kwargs["alternatives"] = [(html, EmailTemplate.CONTENT_TYPE_HTML)]

        super().__init__(**email_kwargs)

        self.template = template
        self.context = context
        self.html = html

    def size_in_bytes(self) -> int:
        """Return the size of the underlying message in bytes."""
        return len(self.message().as_bytes())

    def _user(self, email: str) -> settings.AUTH_USER_MODEL | None:
        """
        Fetch a user matching the 'to' email address.

        This method assumes that emails are unique. If users share emails,
        then we return None, as we cannot determine who is the correct
        recipient.

        """
        email = email.strip().lower()
        if not email:
            return None
        try:
            return User.objects.get(email__iexact=email)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

    @transaction.atomic
    def send(
        self,
        *,
        log_sent_emails: bool = LOG_SENT_EMAILS,
        fail_silently: bool = False,
    ) -> int:
        """
        Send the email and add to audit log.

        This method first sends the email using the underlying
        send method inherited from EmailMultiMessage. If any messages
        are sent (return value > 0), then the message is logged.

        """
        sent = super().send(fail_silently=fail_silently)
        if not log_sent_emails:
            return sent
        if not sent:
            return 0
        return len(LoggedMessage.objects.log(self))


class LoggedMessageManager(models.Manager):
    def log(self, message: AppmailMessage) -> list[LoggedMessage]:
        """Log the sending of emails from an AppmailMessage."""
        return [
            LoggedMessage.objects.create(
                template=message.template,
                to=email,
                user=message._user(email),
                subject=message.subject,
                body=message.body,
                html=message.html,
                context=message.context,
            )
            for email in message.to
        ]


class LoggedMessage(models.Model):
    """Record of emails sent via Appmail."""

    # ensure we record the email address itself, even if we don't have a User object
    to = models.EmailField(help_text=_lazy("Address to which the the Email was sent."))
    # nullable, as sometimes we may have unknown senders / recipients?
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="logged_emails",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )
    template: EmailTemplate = models.ForeignKey(
        EmailTemplate,
        related_name="logged_emails",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=_lazy("The appmail template used."),
    )
    timestamp = models.DateTimeField(
        default=tz_now, help_text=_lazy("When the email was sent."), db_index=True
    )
    subject = models.TextField(blank=True, help_text=_lazy("Email subject line."))
    body = models.TextField(
        "Plain text", blank=True, help_text=_lazy("Plain text content.")
    )
    html = models.TextField("HTML", blank=True, help_text=_lazy("HTML content."))
    context = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text=_lazy("Appmail template context."),
    )

    objects = LoggedMessageManager()

    class Meta:
        get_latest_by = "timestamp"
        verbose_name = "Email message"
        verbose_name_plural = "Email messages sent"
        indexes = (
            # Indexes to help the admin search.
            models.Index(fields=['to']),
            models.Index(fields=['subject']),
        )

    def __repr__(self) -> str:
        return (
            f"<LoggedMessage id:{self.id} template='{self.template_name}' "
            f"to='{self.to}'>"
        )

    def __str__(self) -> str:
        return f"LoggedMessage sent to {self.to} ['{self.template_name}']>"

    @property
    def template_name(self) -> str:
        """Return the name of the template used."""
        if not self.template:
            return ""
        return self.template.name

    def rehydrate(self) -> AppmailMessage:
        """Create a new AppmailMessage message from this email."""
        return AppmailMessage(
            template=self.template, context=self.context, to=[self.to]
        )

    def resend(
        self,
        log_sent_emails: bool = LOG_SENT_EMAILS,
        fail_silently: bool = False,
    ) -> None:
        """Recreate new AppmailMessage from this log and send it."""
        self.rehydrate().send(
            log_sent_emails=log_sent_emails,
            fail_silently=fail_silently,
        )
