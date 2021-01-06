from django.urls import path

import appmail.models
import appmail.views

app_name = "appmail"

urlpatterns = [
    # template paths
    path(
        "templates/<int:template_id>/body.txt",
        appmail.views.render_template_body,
        kwargs={"content_type": "text/plain"},
        name="render_template_body_text",
    ),
    path(
        "templates/<int:template_id>/body.html",
        appmail.views.render_template_body,
        kwargs={"content_type": "text/html"},
        name="render_template_body_html",
    ),
    path(
        "templates/<int:template_id>/subject.txt",
        appmail.views.render_template_subject,
        name="render_template_subject",
    ),
    path("templates/test/", appmail.views.send_test_email, name="send_test_email"),
    # LoggedMessage paths
    path(
        "emails/<int:email_id>/body.txt",
        appmail.views.render_message_body,
        kwargs={"content_type": appmail.models.EmailTemplate.CONTENT_TYPE_PLAIN},
        name="render_message_body_text",
    ),
    path(
        "emails/<int:email_id>/body.html",
        appmail.views.render_message_body,
        kwargs={"content_type": appmail.models.EmailTemplate.CONTENT_TYPE_HTML},
        name="render_message_body_html",
    ),
    path(
        "emails/resend/<int:email_id>/", appmail.views.resend_email, name="resend_email"
    ),
]
