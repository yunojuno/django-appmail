from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import (
    Context,
    Template,
    TemplateDoesNotExist,
    TemplateSyntaxError
)
from django.utils.translation import ugettext_lazy as _lazy

from . import helpers
from .settings import (
    ADD_EXTRA_HEADERS,
    VALIDATE_ON_SAVE,
    CONTEXT_PROCESSORS
)


class EmailTemplateQuerySet(models.query.QuerySet):

    def active(self):
        """Returns active templates only."""
        return self.filter(is_active=True)

    def current(self, name, language=settings.LANGUAGE_CODE):
        """Returns the latest version of a template."""
        return self.active().filter(name=name, language=language).order_by('version').last()

    def version(self, name, version, language=settings.LANGUAGE_CODE):
        """Returns a specific version of a template."""
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
    CONTENT_TYPE_PLAIN = 'text/plain'
    CONTENT_TYPE_HTML = 'text/html'
    CONTENT_TYPES = (CONTENT_TYPE_PLAIN, CONTENT_TYPE_HTML)

    name = models.CharField(
        _lazy('Template name'),
        max_length=100,
        help_text=_lazy("Template name - must be unique for a given language/version combination."),
        db_index=True
    )
    description = models.CharField(
        _lazy('Description'),
        max_length=100,
        help_text=_lazy("Optional description. e.g. used to differentiate variants ('new header')."),  # noqa
        blank=True
    )
    # language is free text and not a choices field as we make no assumption
    # as to how the end user is storing / managing languages.
    language = models.CharField(
        _lazy('Language'),
        max_length=20,
        default=settings.LANGUAGE_CODE,
        help_text=_lazy(
            "Used to support localisation of emails, defaults to `settings.LANGUAGE_CODE`, "
            "but can be any string, e.g. 'London', 'NYC'."
        ),
        db_index=True
    )
    version = models.IntegerField(
        _lazy('Version (or variant)'),
        default=0,
        help_text=_lazy("Integer value - can be used for versioning or A/B testing."),
        db_index=True
    )
    subject = models.CharField(
        _lazy('Subject line template'),
        max_length=100,
        help_text=_lazy("Email subject line (may contain template variables)."),
    )
    body_text = models.TextField(
        _lazy('Plain text template'),
        help_text=_lazy("Plain text content (may contain template variables)."),
    )
    body_html = models.TextField(
        _lazy('HTML template'),
        help_text=_lazy("HTML content (may contain template variables)."),
    )
    test_context = JSONField(
        default=dict,
        blank=True,
        help_text=_lazy("Dummy JSON used for test rendering (set automatically on first save).")
    )
    is_active = models.BooleanField(
        _lazy("Active (live)"),
        help_text=_lazy("Set to False to remove from `current` queryset."),
        default=True
    )
    from_email = models.CharField(
        _lazy("Sender"),
        max_length=254,
        help_text=_lazy(
            "Default sender address if none specified. Verbose form is accepted."
        ),
        default=settings.DEFAULT_FROM_EMAIL
    )
    reply_to = models.CharField(
        _lazy("Reply-To"),
        max_length=254,
        help_text=_lazy("Comma separated list of Reply-To recipients."),
        default=settings.DEFAULT_FROM_EMAIL
    )

    objects = EmailTemplateQuerySet().as_manager()

    class Meta:
        unique_together = ("name", "language", "version")

    def __str__(self):
        return "'{}' ({})".format(self.name, self.language)

    def __repr__(self):
        return (
            "<EmailTemplate id={} name='{}' language='{}' version={}>".format(
                self.id, self.name, self.language, self.version
            )
        )

    @property
    def extra_headers(self):
        return{
            'X-Appmail-Template': (
                'name=%s; language=%s; version=%s' % (self.name, self.language, self.version)
            )
        }

    @property
    def reply_to_list(self):
        """Convert the reply_to field to a list."""
        return [a.strip() for a in self.reply_to.split(',')]

    def save(self, *args, **kwargs):
        """Update dummy context on first save and validate template contents.

        Kwargs:
            validate: set to False to bypass template validation; defaults
                to settings.VALIDATE_ON_SAVE.

        """
        if self.pk is None:
            self.test_context = helpers.get_context(
                self.subject +
                self.body_text +
                self.body_html
            )
        validate = kwargs.pop('validate', VALIDATE_ON_SAVE)
        if validate:
            self.clean()
        super(EmailTemplate, self).save(*args, **kwargs)
        return self

    def clean(self):
        """Validate model - specifically that the template can be rendered."""
        validation_errors = {}
        validation_errors.update(self._validate_body(EmailTemplate.CONTENT_TYPE_PLAIN))
        validation_errors.update(self._validate_body(EmailTemplate.CONTENT_TYPE_HTML))
        validation_errors.update(self._validate_subject())
        if validation_errors:
            raise ValidationError(validation_errors)

    def render_subject(self, context, processors=CONTEXT_PROCESSORS):
        """Render subject line."""
        ctx = Context(helpers.patch_context(context, processors))
        return Template(self.subject).render(ctx)

    def _validate_subject(self):
        """Try rendering the body template and capture any errors."""
        try:
            self.render_subject({})
        except TemplateDoesNotExist as ex:
            return {'subject': _lazy("Template does not exist: {}".format(ex))}
        except TemplateSyntaxError as ex:
            return {'subject': str(ex)}
        else:
            return {}

    def render_body(self, context, content_type=CONTENT_TYPE_PLAIN, processors=CONTEXT_PROCESSORS):
        """Render email body in plain text or HTML format."""
        assert content_type in EmailTemplate.CONTENT_TYPES, _lazy("Invalid content type.")
        ctx = Context(helpers.patch_context(context, processors))
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            return Template(self.body_text).render(ctx)
        if content_type == EmailTemplate.CONTENT_TYPE_HTML:
            return Template(self.body_html).render(ctx)

    def _validate_body(self, content_type):
        """Try rendering the body template and capture any errors."""
        assert content_type in EmailTemplate.CONTENT_TYPES, _lazy("Invalid content type.")
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            field_name = 'body_text'
        if content_type == EmailTemplate.CONTENT_TYPE_HTML:
            field_name = 'body_html'
        try:
            self.render_body({}, content_type=content_type)
        except TemplateDoesNotExist as ex:
            return {field_name: _lazy("Template does not exist: {}".format(ex))}
        except TemplateSyntaxError as ex:
            return {field_name: str(ex)}
        else:
            return {}

    def create_message(self, context, **email_kwargs):
        """
        Return populated EmailMultiAlternatives object.

        This function is a helper that will render the template subject and
        plain text / html content, as well as populating all of the standard
        EmailMultiAlternatives properties.

            >>> template = EmailTemplate.objects.get_latest('order_summary')
            >>> context = {'first_name': "Bruce", 'last_name'="Lee"}
            >>> email = template.create_message(context, to=['bruce@kung.fu'])
            >>> email.send()

        The function supports all of the standard EmailMultiAlternatives
        constructor kwargs except for 'subject', 'body' and 'alternatives' - as
        these are set from the template (subject, body_text and body_html).

        """
        for kw in ('subject', 'body', 'alternatives'):
            assert kw not in email_kwargs, _lazy("Invalid create_message kwarg: '{}'".format(kw))
        subject = self.render_subject(context)
        body = self.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN)
        html = self.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_HTML)
        email_kwargs['reply_to'] = email_kwargs.get('reply_to') or self.reply_to_list
        email_kwargs['from_email'] = email_kwargs.get('from_email') or self.from_email
        if ADD_EXTRA_HEADERS:
            email_kwargs['headers'] = email_kwargs.get('headers', {})
            email_kwargs['headers'].update(self.extra_headers)
        # alternatives is a list of (content, mimetype) tuples
        # https://github.com/django/django/blob/master/django/core/mail/message.py#L435
        return EmailMultiAlternatives(
            subject=subject,
            body=body,
            alternatives=[(html, EmailTemplate.CONTENT_TYPE_HTML)],
            **email_kwargs
        )

    def clone(self):
        """Create a copy of the current object, increase version by 1."""
        self.pk = None
        self.version += 1
        return self.save()
