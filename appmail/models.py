# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.template import Context, Template


class EmailTemplate(models.Model):

    """
    Email template. Contains HTML and TXT variants.

    Each Template object has a unique name-language combination, which
    means that localisation of templates is managed through having multiple
    objects with the same name - there is no inheritence model. This is to
    keep it simple:

        order-confirmation:en
        order-confirmation:de
        order-confirmation:fr

    Templates contain HTML and plain text content.

    """

    name = models.CharField(
        max_length=100,
        help_text="Name used in code to retrieve template.",
        db_index=True
    )
    # language is free text, and not a choices field as we make no assumption
    # as to how the end user is storing / managing languages.
    language = models.CharField(
        max_length=20,
        help_text=(
            "Template language - unique key in conjunction with name."
        ),
        db_index=True
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Optional template description (purpose, audience, etc.)"
    )
    subject = models.CharField(
        max_length=100,
        help_text="Email subject line (may contain template variables)."
    )
    text = models.TextField(
        help_text="Plain text content (may contain template variables)."
    )
    html = models.TextField(
        help_text="HTML content (may contain template variables)."
    )
    # TODO: validation is a nice idea, but not a v1 requirement
    # context_variables = models.TextField(
    #     null=True,
    #     blank=True,
    #     help_text=(
    #         "Optional comma-separated list of variable names, "
    #         "used to validate the email context."
    #     )
    # )

    class Meta:
        unique_together = ("name", "language")

    def render(self, context):
        """
        Return the subject, plain text and HTML rendered content.

        This method returns a 3-tuple object that contains the rendered
        subject line, plain text and HTML content.

            >>> template = EmailTemplate.objects.get(name='order-summary', language='english')  # noqa
            >>> subject, text, html = template.render(context)

        """
        return (
            self.render_subject(context),
            self.render_text(context),
            self.render_html(context)
        )

    def render_subject(self, context):
        """Render subject line."""
        return Template(self.subject).render(Context(context))

    def render_text(self, context):
        """Render plain text content."""
        return Template(self.text).render(Context(context))

    def render_html(self, context):
        """Render HTML content."""
        return Template(self.html).render(Context(context))
