# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory

from .. import views
from ..compat import reverse, mock
from ..forms import EmailTestForm
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
            template.render_subject(template.test_context)
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
                template.test_context,
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
                template.test_context,
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

    def test_send_test_emails_GET(self):
        user = User.objects.create(username='admin', password='password', is_staff=True)
        template = self.template
        url = '{}?templates={}'.format(
            reverse('appmail:send_test_email'),
            template.pk
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.client.force_login(user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, template.name)

    @mock.patch.object(EmailTestForm, 'send_emails')
    def test_send_test_emails_POST(self, mock_send):
        user = User.objects.create(username='admin', password='password', is_staff=True)
        template = self.template
        url = '{}?templates={}'.format(
            reverse('appmail:send_test_email'),
            template.pk
        )
        self.client.force_login(user)
        payload = {
            'to': 'fred@example.com',
            'cc': '',
            'bcc': '',
            'context': '',
            'from_email': 'donotreply@example.com',
            'templates': template.pk
        }
        response = self.client.post(url, payload)
        self.assertEqual(mock_send.call_count, 1)
        mock_send.assert_called_once_with(response.wsgi_request)
        self.assertEqual(response.status_code, 302)

        # check that bad response returns 422
        response = self.client.post(url, {})
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(response.status_code, 422)
