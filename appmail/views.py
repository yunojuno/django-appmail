# -*- coding: utf-8 -*-
"""
These views are intended for use in rendering email templates
within the admin site, and supporting preview functionality.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _

from .compat import reverse
from .forms import MultiEmailTestForm, MultiEmailTemplateField, EmailTestForm
from .models import EmailTemplate

logger = logging.getLogger(__name__)


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


@user_passes_test(lambda u: u.is_staff)
def send_test_emails(request):
    """Intermediate admin action page for sending multiple test emails."""
    if request.method == 'GET':
        # we're using the form field to parse the querystring so that
        # we are consistent - if it parses here, it'll parse in the POST
        field = MultiEmailTemplateField()
        templates = field.to_python(request.GET['templates'])
        form = MultiEmailTestForm(initial=request.GET)
        return render(
            request,
            'appmail/send_test_emails.html',
            {
                'form': form,
                'opts': EmailTemplate._meta,
                'templates': templates
            }
        )
    elif request.method == 'POST':
        form = MultiEmailTestForm(request.POST)
        if form.is_valid():
            for template, email in form.emails():
                try:
                    email.send()
                    messages.success(
                        request,
                        _("Sent test email '%s' to %s" % (template.name, ', '.join(email.to)))
                    )
                except Exception as ex:
                    logger.exception("Error sending test email")
                    messages.error(request, _("Error sending test email '%s': %s" % (template.name, ex)))  # noqa
        else:
            messages.error(request, _("Error sending test emails"))

        return HttpResponseRedirect(reverse('admin:appmail_emailtemplate_changelist'))


@user_passes_test(lambda u: u.is_staff)
def send_test_email(request, template_id):
    """Intermediate admin action page for sending a single test email."""
    template = get_object_or_404(EmailTemplate, id=template_id)

    if request.method == 'GET':
        form = EmailTestForm(template)

    elif request.method == 'POST':
        form = EmailTestForm(template, request.POST)
        if form.is_valid():
            email = form.email()
            try:
                email.send()
            except Exception as ex:
                logger.exception("Error sending test email")
                messages.error(request, _("Error sending test email '%s': %s" % (template.name, ex)))  # noqa
            else:
                messages.success(
                    request,
                    _("Sent test email '%s' to %s" % (template.name, ', '.join(email.to)))
                )
            finally:
                return HttpResponseRedirect(reverse('admin:appmail_emailtemplate_changelist'))

    return render(
        request,
        'appmail/send_test_email.html',
        {
            'form': form,
            'template': template,
            # opts are used for rendering some page furniture - breadcrumbs etc.
            'opts': EmailTemplate._meta,
        }
    )
