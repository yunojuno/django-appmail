from email.mime.image import MIMEImage
from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.test import TestCase

from appmail.models import AppmailMessage, EmailTemplate


class EmailTemplateQuerySetTests(TestCase):
    def test_active(self):
        template1 = EmailTemplate(name="test1", language="en-us").save()
        _ = EmailTemplate(name="test2", language="en-us", is_active=False).save()
        self.assertEqual(EmailTemplate.objects.active().get(), template1)

    def test_current(self):
        # manually setting the version in the wrong order, so the first
        # template is actually the last, when ordered by version.
        template1 = EmailTemplate(name="test", language="en-us", version=1).save()
        _ = EmailTemplate(name="test", language="en-us", version=0).save()
        self.assertEqual(EmailTemplate.objects.current("test"), template1)
        self.assertEqual(
            EmailTemplate.objects.current("test", language="klingon"), None
        )

    def test_version(self):
        template1 = EmailTemplate(name="test", language="en-us", version=1).save()
        template2 = EmailTemplate(name="test", language="en-us", version=0).save()
        self.assertEqual(EmailTemplate.objects.version("test", 1), template1)
        self.assertEqual(EmailTemplate.objects.version("test", 0), template2)


class EmailTemplateTests(TestCase):
    """appmail.models.EmailTemplate model tests."""

    def test_defaults(self):
        template = EmailTemplate()
        self.assertEqual(template.language, settings.LANGUAGE_CODE)
        self.assertEqual(template.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(template.reply_to, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(template.reply_to_list, [settings.DEFAULT_FROM_EMAIL])
        self.assertEqual(template.version, 0)

        template.reply_to = "fred@example.com, ginger@example.com"
        self.assertEqual(
            template.reply_to_list, ["fred@example.com", "ginger@example.com"]
        )

    @mock.patch.object(EmailTemplate, "clean")
    def test_save(self, mock_clean):
        template = EmailTemplate(
            subject="test ßmail",
            body_text="this is plain text",
            body_html="this is <b>html</b>",
        )
        with mock.patch("appmail.models.VALIDATE_ON_SAVE", False):
            template.save()
            self.assertEqual(mock_clean.call_count, 0)
        with mock.patch("appmail.models.VALIDATE_ON_SAVE", True):
            template.save()
            self.assertEqual(mock_clean.call_count, 1)
            # test the override
            template.save(validate=False)
            self.assertEqual(mock_clean.call_count, 1)

    @mock.patch.object(EmailTemplate, "render_subject")
    def test__validate_subject(self, mock_render):
        template = EmailTemplate()
        mock_render.side_effect = TemplateDoesNotExist("foo.html")
        self.assertEqual(
            template._validate_subject(),
            {"subject": "Template does not exist: foo.html"},
        )
        mock_render.side_effect = TemplateSyntaxError("No can do")
        self.assertEqual(template._validate_subject(), {"subject": "No can do"})
        mock_render.side_effect = None
        self.assertEqual(template._validate_subject(), {})
        mock_render.side_effect = Exception("Something else")
        self.assertRaises(Exception, template._validate_subject)

    @mock.patch.object(EmailTemplate, "render_body")
    def test__validate_body(self, mock_render):
        template = EmailTemplate()
        mock_render.side_effect = TemplateDoesNotExist("foo.html")
        self.assertEqual(
            template._validate_body(content_type=EmailTemplate.CONTENT_TYPE_PLAIN),
            {"body_text": "Template does not exist: foo.html"},
        )
        mock_render.side_effect = TemplateSyntaxError("No can do")
        self.assertEqual(
            template._validate_body(content_type=EmailTemplate.CONTENT_TYPE_HTML),
            {"body_html": "No can do"},
        )
        mock_render.side_effect = None
        self.assertEqual(template._validate_body(EmailTemplate.CONTENT_TYPE_HTML), {})
        mock_render.side_effect = Exception("Something else")
        self.assertRaises(Exception, template._validate_body)

    @mock.patch.object(EmailTemplate, "_validate_body")
    def test_clean(self, mock_body):
        template = EmailTemplate()
        template.clean()
        mock_body.return_value = {"body_text": "Template not found"}
        self.assertRaises(ValidationError, template.clean)

    def test_render_subject(self):
        template = EmailTemplate(subject="Hello {{ first_name }}")
        subject = template.render_subject({"first_name": "fråd"})
        self.assertEqual(subject, "Hello fråd")

    def test_render_body(self):
        template = EmailTemplate(
            body_text="Hello {{ first_name }}",
            body_html="<h1>Hello {{ first_name }}</h1>",
        )
        context = {"first_name": "fråd"}
        self.assertEqual(template.render_body(context), "Hello fråd")
        self.assertEqual(
            template.render_body(
                context, content_type=EmailTemplate.CONTENT_TYPE_PLAIN
            ),
            "Hello fråd",
        )
        self.assertEqual(
            template.render_body(context, content_type=EmailTemplate.CONTENT_TYPE_HTML),
            "<h1>Hello fråd</h1>",
        )
        self.assertRaises(ValueError, template.render_body, context, content_type="foo")

    def test_clone_template(self):
        template = EmailTemplate(
            name="Test template", language="en-us", version=0
        ).save()
        pk = template.pk
        clone = template.clone()
        template = EmailTemplate.objects.get(id=pk)
        self.assertEqual(clone.name, template.name)
        self.assertEqual(clone.language, template.language)
        self.assertEqual(clone.version, 1)
        self.assertNotEqual(clone.id, template.id)


class AppmailMessageTests(TestCase):
    def test_create_message(self):
        template = EmailTemplate(
            subject="Welcome message",
            body_text="Hello {{ first_name }}",
            body_html="<h1>Hello {{ first_name }}</h1>",
        )
        context = {"first_name": "fråd"}
        message = AppmailMessage.from_template(template, context)
        self.assertIsInstance(message, EmailMultiAlternatives)
        self.assertEqual(message.subject, "Welcome message")
        self.assertEqual(message.body, "Hello fråd")
        self.assertEqual(
            message.alternatives,
            [("<h1>Hello fråd</h1>", EmailTemplate.CONTENT_TYPE_HTML)],
        )
        self.assertEqual(message.to, [])
        self.assertEqual(message.cc, [])
        self.assertEqual(message.bcc, [])
        self.assertEqual(message.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(message.reply_to, [settings.DEFAULT_FROM_EMAIL])

        message = AppmailMessage.from_template(
            template,
            context,
            to=["bruce@kung.fu"],
            cc=["fred@example.com"],
            bcc=["ginger@example.com"],
            from_email="Fred <fred@example.com>",
        )
        self.assertEqual(message.to, ["bruce@kung.fu"])
        self.assertEqual(message.cc, ["fred@example.com"])
        self.assertEqual(message.bcc, ["ginger@example.com"])
        self.assertEqual(message.from_email, "Fred <fred@example.com>")
        # and so on - not going to test every property.

        # but we will check the three illegal kwargs
        with self.assertRaisesMessage(
            ValueError, "Invalid argument: 'subject' is set from the template."
        ):
            AppmailMessage.from_template(template, {}, subject="foo")
        with self.assertRaisesMessage(
            ValueError, "Invalid argument: 'body' is set from the template."
        ):
            AppmailMessage.from_template(template, {}, body="foo")
        with self.assertRaisesMessage(
            ValueError, "Invalid argument: 'alternatives' is set from the template."
        ):
            AppmailMessage.from_template(template, {}, alternatives="foo")

    def test_create_message__with_attachments__allowed(self):
        template = EmailTemplate(
            subject="Welcome {{ first_name }}",
            body_text="Hello {{ first_name }}",
            body_html="<h1>Hello {{ first_name }}</h1>",
            supports_attachments=True,
        )
        AppmailMessage.from_template(
            template, {}, attachments=[mock.Mock(spec=MIMEImage)]
        )

    def test_create_message__with_attachments__disallowed(self):
        template = EmailTemplate(
            subject="Welcome {{ first_name }}",
            body_text="Hello {{ first_name }}",
            body_html="<h1>Hello {{ first_name }}</h1>",
            supports_attachments=False,
        )
        with self.assertRaisesMessage(
            ValueError, "Email template does not support attachments."
        ):
            AppmailMessage.from_template(
                template, {}, attachments=[mock.Mock(spec=MIMEImage)]
            )

    def test_create_message__special_characters(self):
        template = EmailTemplate(
            subject="Welcome {{ first_name }}",
            body_text="Hello {{ first_name }}",
            body_html="<h1>Hello {{ first_name }}</h1>",
        )

        context = {"first_name": "Test & Company"}
        message = AppmailMessage.from_template(template, context)
        self.assertIsInstance(message, EmailMultiAlternatives)
        self.assertEqual(message.subject, "Welcome Test & Company")
        self.assertEqual(message.body, "Hello Test & Company")
        self.assertEqual(
            message.alternatives,
            [("<h1>Hello Test &amp; Company</h1>", EmailTemplate.CONTENT_TYPE_HTML)],
        )

    def test_create_message__special_characters__complex_context(self):
        template = EmailTemplate(
            subject="Hello {{ user.first_name }} and welcome to {{ company_name }}",
            body_text="Hello {{ user.first_name }} and welcome to {{ company_name }}",
            body_html=(
                "<h1>Hello {{ user.first_name }}</h1></br><p>"
                "Welcome to {{ company_name }}</p>"
            ),
        )

        context = {
            "user": {"first_name": "Test & Company"},
            "company_name": "Me & Co Inc",
        }
        message = AppmailMessage.from_template(template, context)
        self.assertIsInstance(message, EmailMultiAlternatives)
        self.assertEqual(
            message.subject, "Hello Test & Company and welcome to Me & Co Inc"
        )
        self.assertEqual(
            message.body, "Hello Test & Company and welcome to Me & Co Inc"
        )
        self.assertEqual(
            message.alternatives,
            [
                (
                    "<h1>Hello Test &amp; Company</h1></br><p>"
                    "Welcome to Me &amp; Co Inc</p>",
                    EmailTemplate.CONTENT_TYPE_HTML,
                )
            ],
        )
