# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.test import TestCase

from ..models import EmailTemplate


class EmailTemplateQuerySetTests(TestCase):

    """appmail.models.EmailTemplateQuerySet model tests."""

    def test_current(self):
        # manually setting the version in the wrong order, so the first
        # template is actually the last, when ordered by version.
        template1 = EmailTemplate(name='test', language='en-us', version=1).save()
        template2 = EmailTemplate(name='test', language='en-us', version=0).save()
        self.assertEqual(EmailTemplate.objects.current('test'), template1)
        self.assertEqual(EmailTemplate.objects.current('test', language='klingon'), None)

    def test_version(self):
        template1 = EmailTemplate(name='test', language='en-us', version=1).save()
        template2 = EmailTemplate(name='test', language='en-us', version=0).save()
        self.assertEqual(EmailTemplate.objects.version('test', 1), template1)
        self.assertEqual(EmailTemplate.objects.version('test', 0), template2)


class EmailTemplateTests(TestCase):

    """appmail.models.EmailTemplate model tests."""

    def test_defaults(self):
        template = EmailTemplate()
        self.assertEqual(template.language, settings.LANGUAGE_CODE)
        self.assertEqual(template.version, 0)

    @mock.patch.object(EmailTemplate, 'clean')
    def test_save(self, mock_clean):
        template = EmailTemplate(
            subject='test ßmail',
            body_text='this is plain text',
            body_html='this is <b>html</b>'
        )
        with mock.patch('appmail.models.VALIDATE_ON_SAVE', False):
            template.save()
            self.assertEqual(mock_clean.call_count, 0)
        with mock.patch('appmail.models.VALIDATE_ON_SAVE', True):
            template.save()
            self.assertEqual(mock_clean.call_count, 1)

    @mock.patch.object(EmailTemplate, 'render_subject')
    def test__validate_subject(self, mock_render):
        template = EmailTemplate()
        mock_render.side_effect = TemplateDoesNotExist('foo.html')
        self.assertEqual(
            template._validate_subject(),
            {'subject': "Template does not exist: foo.html"}
        )
        mock_render.side_effect = TemplateSyntaxError('No can do')
        self.assertEqual(
            template._validate_subject(),
            {'subject': "No can do"}
        )
        mock_render.side_effect = None
        self.assertEqual(
            template._validate_subject(),
            {}
        )
        mock_render.side_effect = Exception("Something else")
        self.assertRaises(Exception, template._validate_subject)

    @mock.patch.object(EmailTemplate, 'render_body')
    def test__validate_body(self, mock_render):
        template = EmailTemplate()
        mock_render.side_effect = TemplateDoesNotExist('foo.html')
        self.assertEqual(
            template._validate_body(content_type=EmailTemplate.CONTENT_TYPE_PLAIN),
            {'body_text': "Template does not exist: foo.html"}
        )
        mock_render.side_effect = TemplateSyntaxError('No can do')
        self.assertEqual(
            template._validate_body(content_type=EmailTemplate.CONTENT_TYPE_HTML),
            {'body_html': "No can do"}
        )
        mock_render.side_effect = None
        self.assertEqual(template._validate_body(EmailTemplate.CONTENT_TYPE_HTML), {})
        mock_render.side_effect = Exception("Something else")
        self.assertRaises(Exception, template._validate_body)

    @mock.patch.object(EmailTemplate, '_validate_body')
    def test_clean(self, mock_body):
        template = EmailTemplate()
        template.clean()
        mock_body.return_value = {'body_text': 'Template not found'}
        self.assertRaises(ValidationError, template.clean)

    def test_render_subject(self):
        template = EmailTemplate(subject='Hello {{ first_name }}')
        subject = template.render_subject({'first_name': 'fråd'})
        self.assertEqual(subject, 'Hello fråd')

    def test_render_body(self):
        template = EmailTemplate(
            body_text='Hello {{ first_name }}',
            body_html='<h1>Hello {{ first_name }}</h1>'
        )
        context = {'first_name': 'fråd'}
        self.assertEqual(template.render_body(context), 'Hello fråd')
        self.assertEqual(
            template.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN),
            'Hello fråd'
        )
        self.assertEqual(
            template.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_HTML),
            '<h1>Hello fråd</h1>'
        )
        self.assertRaises(
            AssertionError,
            template.render_body,
            context,
            content_type='foo'
        )

    def test_create_message(self):
        template = EmailTemplate(
            subject='Welcome message',
            body_text='Hello {{ first_name }}',
            body_html='<h1>Hello {{ first_name }}</h1>'
        )
        context = {'first_name': 'fråd'}
        message = template.create_message(context)
        self.assertIsInstance(message, EmailMultiAlternatives)
        self.assertEqual(message.subject, 'Welcome message')
        self.assertEqual(message.body, 'Hello fråd')
        self.assertEqual(
            message.alternatives,
            [('<h1>Hello fråd</h1>', EmailTemplate.CONTENT_TYPE_HTML)]
        )
        self.assertEqual(message.to, [])
        self.assertEqual(message.cc, [])
        self.assertEqual(message.bcc, [])

        message = template.create_message(
            context,
            to=['bruce@kung.fu'],
            cc=['fred@example.com'],
            bcc=['ginger@example.com']
        )
        self.assertEqual(message.to, ['bruce@kung.fu'])
        self.assertEqual(message.cc, ['fred@example.com'])
        self.assertEqual(message.bcc, ['ginger@example.com'])
        # and so on - not going to test every property.

        # but we will check the three illegal kwargs
        self.assertRaises(AssertionError, template.create_message, {}, subject='foo')
        self.assertRaises(AssertionError, template.create_message, {}, body='foo')
        self.assertRaises(AssertionError, template.create_message, {}, alternatives='foo')
