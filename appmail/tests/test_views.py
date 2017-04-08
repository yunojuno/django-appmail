# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory

from .. import views
from ..compat import reverse
from ..models import EmailTemplate


class ViewTests(TestCase):

    """appmail.helpers module tests."""

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.template = EmailTemplate(
            subject='ßello, {{user.first_name}}',
            body_text='ßello,\n{{user.first_name}}',
            body_html="ßello, <b>{{user.first_name}}</b>"
        ).save()
        self.subject_url = reverse(
            'appmail:render_template_subject',
            kwargs={'template_id': self.template.id}
        )
        self.body_text_url = reverse(
            'appmail:render_template_body_text',
            kwargs={'template_id': self.template.id}
        )
        self.body_html_url = reverse(
            'appmail:render_template_body_html',
            kwargs={'template_id': self.template.id}
        )

    def test_render_template_subject(self):
        template = self.template
        request = self.factory.get(self.subject_url)
        # check that non-staff are denied
        request.user = AnonymousUser()
        response = views.render_template_subject(request, template.id)
        self.assertEqual(response.status_code, 302)
        # non-staff user
        request.user = User()
        response = views.render_template_subject(request, template.id)
        self.assertEqual(response.status_code, 302)
        # staff user
        request.user.is_staff = True
        response = views.render_template_subject(request, template.id)
        self.assertEqual(response.status_code, 200)
        # should render the template with the dummy context
        self.assertEqual(
            response.content.decode('utf-8'),
            template.render_subject(template.subject_context)
        )

    def test_render_template_body(self):
        template = self.template
        request = self.factory.get(self.body_text_url)
        # check that non-staff are denied
        request.user = AnonymousUser()
        response = views.render_template_body(
            request,
            template.id,
            EmailTemplate.CONTENT_TYPE_PLAIN
        )
        self.assertEqual(response.status_code, 302)
        # non-staff user
        request.user = User()
        response = views.render_template_body(
            request,
            template.id,
            EmailTemplate.CONTENT_TYPE_PLAIN
        )
        self.assertEqual(response.status_code, 302)
        # staff user
        request.user.is_staff = True
        response = views.render_template_body(
            request,
            template.id,
            EmailTemplate.CONTENT_TYPE_PLAIN
        )
        self.assertEqual(response.status_code, 200)
        # should render the template with the dummy context
        self.assertEqual(
            response.content.decode('utf-8'),
            template.render_body(
                template.body_text_context,
                EmailTemplate.CONTENT_TYPE_PLAIN
            )
        )
        # now check the HTML version
        response = views.render_template_body(
            request,
            template.id,
            EmailTemplate.CONTENT_TYPE_HTML
        )
        self.assertEqual(
            response.content.decode('utf-8'),
            template.render_body(
                template.body_html_context,
                EmailTemplate.CONTENT_TYPE_HTML
            )
        )

        # now check the HTML version
        response = views.render_template_body(
            request,
            template.id,
            "foo"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content.decode('utf-8'),
            "Invalid content_type specified."
        )
