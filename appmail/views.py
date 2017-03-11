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
    context = request.GET.dict()
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
    format = request.GET.get('format', 'plain')
    context = request.GET.dict()
    if format == 'plain':
        return HttpResponse(
            template.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN),
            content_type=EmailTemplate.CONTENT_TYPE_PLAIN
        )
    elif format == 'html':
        return HttpResponse(
            template.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_HTML),
            content_type=EmailTemplate.CONTENT_TYPE_HTML
        )
    else:
        return HttpResponse(
            "Invalid template format: '{}' - must be 'plain' or 'html'.".format(format),
            content_type='text/plain',
            status=400
        )
