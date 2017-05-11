# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.module_loading import import_string

# Validate that EmailTemplate can be rendered without
# error on each save. Defaults to True.
VALIDATE_ON_SAVE = getattr(settings, 'APPMAIL_VALIDATE_ON_SAVE', True)
# used as the from_email address for sending emails
DEFAULT_SENDER = getattr(settings, 'APPMAIL_DEFAULT_SENDER', None)
# if True then add X-Appmail-* headers to outgoung email objects
ADD_EXTRA_HEADERS = getattr(settings, 'APPMAIL_ADD_HEADERS', True)
# list of context processor functions applied on each render
CONTEXT_PROCESSORS = [import_string(s) for s in getattr(settings, 'APPMAIL_CONTEXT_PROCESSORS', [])]  # noqa
