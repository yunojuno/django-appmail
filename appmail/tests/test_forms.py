# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.test import TestCase

from ..compat import mock
from ..forms import MultiEmailField, MultiEmailTemplateField, EmailTestForm
from ..models import EmailTemplate


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
