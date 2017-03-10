# -*- coding: utf-8 -*-
from django.core.mail import EmailMultiAlternatives

from .models import EmailTemplate


def render_as_email(template_name, language, context,
                    from_email=None, to=None, bcc=None,
                    connection=None, attachments=None, headers=None,
                    cc=None, reply_to=None):
    """
    Return populated EmailMultiAlternatives object.

    This function is a helper that will render the template subject and
    plain text / html content.

        >>> context = {'first_name': "Bruce", 'last_name'="Lee"}
        >>> email = render_email('order-summary', 'en', context, to=['bruce@kung.fu'])
        >>> email.send()

    The function supports all of the standard EmailMultiAlternatives constructor kwargs
    except for 'subject', 'body' and 'alternatives' - as these are set from the
    template (subject, text and html).

    """
    template = EmailTemplate.objects.get(name=template_name, language=language)
    subject, body, html = template.render(context)
    # alternatives is a list of (content, mimetype) tuples
    # https://github.com/django/django/blob/master/django/core/mail/message.py#L435
    alternatives = [(html, 'text/html')]
    return EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        bcc=bcc,
        connection=connection,
        attachments=attachments,
        headers=headers,
        alternatives=alternatives,
        cc=cc,
        reply_to=reply_to
    )
