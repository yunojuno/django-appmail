# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.forms import Textarea
from django.http import HttpRequest
from django.test import TestCase

from ..compat import mock
from ..forms import (
    EmailTestForm,
    JSONWidget,
    MultiEmailField,
    MultiEmailTemplateField,
)
from ..models import EmailTemplate


class JSONWidgetTests(TestCase):

    def test_format_value(self):
        widget = JSONWidget()
        self.assertEqual(widget.format_value(None), '{}')
        self.assertEqual(widget.format_value(''), '{}')
        self.assertEqual(widget.format_value('{"foo": true}'), '{\n    "foo": true\n}')
        self.assertRaises(AssertionError, widget.format_value, {"foo": True})

    def test_render(self):
        widget = JSONWidget()
        textarea = Textarea()
        for val in [None, '', '{"foo": true}']:
            self.assertEqual(
                widget.render('test', val),
                textarea.render('test', widget.format_value(val), attrs=widget.DEFAULT_ATTRS)
            )


class MultiEmailFieldTests(TestCase):

    def test_to_python(self):
        form = MultiEmailField()
        self.assertEqual(form.to_python(None), [])
        self.assertEqual(form.to_python(''), [])
        self.assertEqual(form.to_python('fred@example.com'), ['fred@example.com'])
        self.assertEqual(
            form.to_python('fred@example.com , ginger@example.com'),
            ['fred@example.com', 'ginger@example.com']
        )
        self.assertEqual(
            form.to_python(['fred@example.com']),
            ['fred@example.com']
        )

    def test_validate(self):
        form = MultiEmailField()
        form.validate(['fred@example.com'])
        form.validate(form.to_python('fred@example.com, ginger@example.com'))
        # single email address fails validation - must be a list
        self.assertRaises(ValidationError, form.validate, 'fred@example.com')


class MultiEmailTemplateFieldTests(TestCase):

    @mock.patch.object(EmailTemplate.objects, 'filter')
    def test_to_python(self, mock_filter):
        form = MultiEmailTemplateField()
        self.assertEqual(list(form.to_python(None)), list(EmailTemplate.objects.none()))
        self.assertEqual(list(form.to_python('')), list(EmailTemplate.objects.none()))
        qs = EmailTemplate.objects.none()
        self.assertEqual(form.to_python(qs), qs)
        form.to_python('1, 2')
        mock_filter.assert_called_once_with(pk__in=[1, 2])


class EmailTestFormTests(TestCase):

    def test_clean_context(self):
        form = EmailTestForm()
        form.cleaned_data = {'context': 'true'}
        self.assertEqual(form.clean_context(), True)
        form.cleaned_data['context'] = True
        self.assertRaises(ValidationError, form.clean_context)

    def test__create_message(self):
        form = EmailTestForm()
        form.cleaned_data = {
            'context': {'foo': 'bar'},
            'to': ['fred@example.com'],
            'cc': [],
            'bcc': [],
            'from_email': 'donotreply@example.com'
        }
        template = EmailTemplate()
        email = form._create_message(template)
        self.assertEqual(email.from_email, 'donotreply@example.com')
        self.assertEqual(email.to, ['fred@example.com'])
        self.assertEqual(email.cc, [])
        self.assertEqual(email.bcc, [])

    @mock.patch('appmail.forms.messages')
    @mock.patch.object(EmailMultiAlternatives, 'send')
    def test_send_emails(self, mock_send, mock_messages):
        template = EmailTemplate()
        form = EmailTestForm()
        form.cleaned_data = {
            'context': {'foo': 'bar'},
            'to': ['fred@example.com'],
            'cc': [],
            'bcc': [],
            'from_email': 'donotreply@example.com',
            'templates': [template]
        }
        request = HttpRequest()
        form.send_emails(request)
        mock_send.assert_called_once()
        mock_messages.success.assert_called_once()

        # test email failure
        mock_send.side_effect = Exception()
        form.send_emails(request)
        mock_messages.error.assert_called_once()
