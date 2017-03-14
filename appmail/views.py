# -*- coding: utf-8 -*-
"""
These views are intended for use in rendering email templates
within the admin site, and supporting preview functionality.
"""
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from .models import EmailTemplate


@user_passes_test(lambda u: u.is_staff)
def render_template_subject(request, template_id):
    """
    Render the template subject.

    Any querystring params passed through on the url will be added to a
    dict that is passed in as the template context, so if the templates
    includes `{{ first_name }}`, you can add ?first_name=fred to the
    querystring and it will be rendered.

    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    context = template.subject_context
    print context
    return HttpResponse(template.render_subject(context), content_type='text/plain')


@user_passes_test(lambda u: u.is_staff)
def render_template_body(request, template_id):
    """
    Render the template body as plain text or HTML.

    The querystring parameter 'format' is used to determine how the body
    is rendered, and must be either 'plain' or 'html'.

    Any additional querystring params passed through on the url will be
    added to a dict that is passed in as the template context, so if the
    template includes `{{ first_name }}`, you can add `?first_name=fred`
    to the querystring and it will be rendered.

    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    content_type = 'text/{}'.format(request.GET.get('format', 'plain'))
    if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
        context = template.body_text_context
    elif content_type == EmailTemplate.CONTENT_TYPE_HTML:
        context = template.body_html_context
    html = template.render_body(context, content_type)
    return HttpResponse(html, content_type=content_type)
