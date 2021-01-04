"""Views supporting template previews in admin site."""
from __future__ import annotations

import json
import logging

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms import EmailTestForm, MultiEmailTemplateField
from .helpers import merge_dicts
from .models import EmailTemplate, LoggedMessage

logger = logging.getLogger(__name__)


@user_passes_test(lambda u: u.is_staff)
@xframe_options_sameorigin
def render_template_subject(request: HttpRequest, template_id: int) -> HttpResponse:
    """Render the template subject."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    html = template.render_subject(template.test_context)
    return HttpResponse(html, content_type="text/plain")


@user_passes_test(lambda u: u.is_staff)
@xframe_options_sameorigin
def render_template_body(
    request: HttpRequest, template_id: int, content_type: str
) -> HttpResponse:
    """Render the template body as plain text or HTML."""
    template = get_object_or_404(EmailTemplate, id=template_id)
    if content_type in (
        EmailTemplate.CONTENT_TYPE_PLAIN,
        EmailTemplate.CONTENT_TYPE_HTML,
    ):
        html = template.render_body(template.test_context, content_type)
        return HttpResponse(html, content_type=content_type)
    # do not return the content_type to the user, as it is
    # user-generated and _could_ be a vulnerability.
    return HttpResponse("Invalid content_type specified.", status=400)


@user_passes_test(lambda u: u.is_staff)
def send_test_email(request: HttpRequest) -> HttpResponseRedirect:
    """Intermediate admin action page for sending a single test email."""
    # use the field.to_python here as belt-and-braces - if it works here
    # we can be confident that it'll work on the POST.
    templates = MultiEmailTemplateField().to_python(request.GET["templates"])

    if request.method == "GET":
        contexts = merge_dicts(*[t.test_context for t in templates])
        context = json.dumps(contexts, indent=4, sort_keys=True)
        initial = {"templates": request.GET["templates"], "context": context}
        try:
            template = templates.get()
            initial["from_email"] = template.from_email
            initial["reply_to"] = template.reply_to
        except EmailTemplate.MultipleObjectsReturned:
            initial["from_email"] = django_settings.DEFAULT_FROM_EMAIL
            initial["reply_to"] = django_settings.DEFAULT_FROM_EMAIL
        form = EmailTestForm(initial=initial)
        return render(
            request,
            "appmail/send_test_email.html",
            {
                "form": form,
                "templates": templates,
                # opts are used for rendering some page furniture - breadcrumbs etc.
                "opts": EmailTemplate._meta,
            },
        )

    if request.method == "POST":
        form = EmailTestForm(request.POST)
        if form.is_valid():
            form.send_emails(request)
            return HttpResponseRedirect(
                "{}?{}".format(
                    reverse("appmail:send_test_email"), request.GET.urlencode()
                )
            )
        else:
            return render(
                request,
                "appmail/send_test_email.html",
                {
                    "form": form,
                    "templates": templates,
                    # opts are used for rendering some page furniture - breadcrumbs etc.
                    "opts": EmailTemplate._meta,
                },
                status=422,
            )


@user_passes_test(lambda u: u.is_staff)
def resend_email(request: HttpRequest, email_id: int) -> HttpResponseRedirect:
    """Resend a specific LoggedMessage."""
    email = LoggedMessage.objects.get(id=email_id)
    email.resend()
    messages.success(request, _("Resent email to {}".format(email.to)))
    return HttpResponseRedirect(reverse("admin:appmail_loggedmessage_changelist"))


@user_passes_test(lambda u: u.is_staff)
@xframe_options_sameorigin
def render_message_body(
    request: HttpRequest, email_id: int, content_type: str
) -> HttpResponse:
    """Render the email body as plain text or HTML."""
    email = get_object_or_404(LoggedMessage, id=email_id)
    if content_type == EmailTemplate.CONTENT_TYPE_PLAIN:
        return HttpResponse(email.body, content_type=content_type)
    if content_type == EmailTemplate.CONTENT_TYPE_HTML:
        return HttpResponse(email.html, content_type=content_type)
    return HttpResponseBadRequest("Invalid content_type specified.")
