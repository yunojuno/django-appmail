# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
from django.utils.translation import ugettext_lazy as _

from . import helpers
from .settings import VALIDATE_ON_SAVE, ADD_EXTRA_HEADERS


class EmailTemplateQuerySet(models.query.QuerySet):

    def current(self, name, language=settings.LANGUAGE_CODE):
        """Returns the latest version of a template."""
        templates = self.filter(
            name=name,
            language=language
        )
        return templates.order_by('version').last()

    def version(self, name, version, language=settings.LANGUAGE_CODE):
        """Returns a specific version of a template."""
        return self.get(
            name=name,
            language=language,
            version=version
        )


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
        max_length=100,
        help_text=_("Template name - must be unique for a given language/version combination."),
        verbose_name=_('Template name'),
        db_index=True
    )
    description = models.CharField(
        max_length=100,
        help_text=_("Optional description. e.g. used to differentiate variants ('new header')."),
        blank=True
    )
    # language is free text and not a choices field as we make no assumption
    # as to how the end user is storing / managing languages.
    language = models.CharField(
        max_length=20,
        default=settings.LANGUAGE_CODE,
        help_text=_(
            "Used to support localisation of emails, defaults to `settings.LANGUAGE_CODE`, "
            "but can be any string, e.g. 'London', 'NYC'."
        ),
        verbose_name=_('Language'),
        db_index=True
    )
    version = models.IntegerField(
        default=0,
        help_text=_("Integer value - can be used for versioning or A/B testing."),
        verbose_name=_('Version (or variant)'),
        db_index=True
    )
    subject = models.CharField(
        max_length=100,
        help_text=_("Email subject line (may contain template variables)."),
        verbose_name=_('Subject line template')
    )
    body_text = models.TextField(
        help_text=_("Plain text content (may contain template variables)."),
        verbose_name=_('Plain text template')
    )
    body_html = models.TextField(
        help_text=_("HTML content (may contain template variables)."),
        verbose_name=_('HTML template')
    )
    test_context = JSONField(
        default=dict,
        blank=True,
        help_text=_("Dummy JSON used for test rendering (set automatically on first save).")
    )

    objects = EmailTemplateQuerySet().as_manager()

    class Meta:
        unique_together = ("name", "language", "version")

    @property
    def extra_headers(self):
        return{
            'X-Appmail-Template': (
                'name=%s; language=%s; version=%s' % (self.name, self.language, self.version)
            )
        }

    def save(self, *args, **kwargs):
        """Validate template rendering before saving object."""
        if self.pk is None:
            self.test_context = helpers.get_context(
                self.subject +
                self.body_text +
                self.body_html
            )
        if VALIDATE_ON_SAVE:
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

    def render_subject(self, context):
        """Render subject line."""
        return Template(self.subject).render(Context(context))

    def _validate_subject(self):
        """Try rendering the body template and capture any errors."""
        try:
            self.render_subject({})
        except TemplateDoesNotExist as ex:
            return {'subject': _("Template does not exist: {}".format(ex))}
        except TemplateSyntaxError as ex:
            return {'subject': str(ex)}
        else:
            return {}

    def render_body(self, context, content_type=CONTENT_TYPE_PLAIN):
        """Render email body in plain text or HTML format."""
        assert content_type in EmailTemplate.CONTENT_TYPES, _("Invalid content type.")
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            return Template(self.body_text).render(Context(context))
        if content_type == EmailTemplate.CONTENT_TYPE_HTML:
            return Template(self.body_html).render(Context(context))

    def _validate_body(self, content_type):
        """Try rendering the body template and capture any errors."""
        assert content_type in EmailTemplate.CONTENT_TYPES, _("Invalid content type.")
        if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
            field_name = 'body_text'
        if content_type == EmailTemplate.CONTENT_TYPE_HTML:
            field_name = 'body_html'
        try:
            self.render_body({}, content_type=content_type)
        except TemplateDoesNotExist as ex:
            return {field_name: _("Template does not exist: {}".format(ex))}
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
            assert kw not in email_kwargs, _("Invalid create_message kwarg: '{}'".format(kw))
        subject = self.render_subject(context)
        body = self.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN)
        html = self.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_HTML)
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
