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
    """Render the template subject."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    context = template.subject_context
    return HttpResponse(template.render_subject(context), content_type='text/plain')


@user_passes_test(lambda u: u.is_staff)
def render_template_body(request, template_id, content_type):
    """Render the template body as plain text or HTML."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
        context = template.body_text_context
    elif content_type == EmailTemplate.CONTENT_TYPE_HTML:
        context = template.body_html_context
    else:
        # do not return the content_type to the user, as it is
        # user-generated and _could_ be a vulnerability.
        return HttpResponse("Invalid content_type specified.", status=400)
    html = template.render_body(context, content_type)
    return HttpResponse(html, content_type=content_type)
