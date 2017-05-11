# -*- coding: utf-8 -*-
"""
These views are intended for use in rendering email templates
within the admin site, and supporting preview functionality.
"""
import json
import logging

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .compat import reverse
from .forms import MultiEmailTemplateField, EmailTestForm
from .helpers import merge_dicts
from .models import EmailTemplate
from .settings import DEFAULT_SENDER

logger = logging.getLogger(__name__)


@user_passes_test(lambda u: u.is_staff)
@xframe_options_sameorigin
def render_template_subject(request, template_id):
    """Render the template subject."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    html = template.render_subject(template.test_context)
    return HttpResponse(html, content_type='text/plain')


@user_passes_test(lambda u: u.is_staff)
@xframe_options_sameorigin
def render_template_body(request, template_id, content_type):
    """Render the template body as plain text or HTML."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    if content_type in (EmailTemplate.CONTENT_TYPE_PLAIN, EmailTemplate.CONTENT_TYPE_HTML):
        html = template.render_body(template.test_context, content_type)
        return HttpResponse(html, content_type=content_type)
    # do not return the content_type to the user, as it is
    # user-generated and _could_ be a vulnerability.
    return HttpResponse("Invalid content_type specified.", status=400)


@user_passes_test(lambda u: u.is_staff)
def send_test_email(request):
    """Intermediate admin action page for sending a single test email."""
    # use the field.to_python here as belt-and-braces - if it works here
    # we can be confident that it'll work on the POST.
    templates = MultiEmailTemplateField().to_python(request.GET['templates'])
    contexts = merge_dicts(*[t.test_context for t in templates])
    context = json.dumps(contexts, indent=4, sort_keys=True)
    initial = {
        'templates': request.GET['templates'],
        'from_email': DEFAULT_SENDER,
        'context': context
    }
    if request.method == 'GET':
        form = EmailTestForm(initial=initial)
        return render(
            request,
            'appmail/send_test_email.html',
            {
                'form': form,
                'templates': templates,
                # opts are used for rendering some page furniture - breadcrumbs etc.
                'opts': EmailTemplate._meta,
            }
        )

    if request.method == 'POST':
        form = EmailTestForm(request.POST)
        if form.is_valid():
            form.send_emails(request)
            return HttpResponseRedirect(
                '{}?{}'.format(
                    reverse('appmail:send_test_email'),
                    request.GET.urlencode()
                )
            )
        else:
            return render(
                request,
                'appmail/send_test_email.html',
                {
                    'form': form,
                    'templates': templates,
                    # opts are used for rendering some page furniture - breadcrumbs etc.
                    'opts': EmailTemplate._meta,
                },
                status=422
            )
