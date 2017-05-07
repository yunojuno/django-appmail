# -*- coding: utf-8 -*-
from django.conf import settings

# Validate that EmailTemplate can be rendered without
# error on each save. Defaults to True.
VALIDATE_ON_SAVE = getattr(settings, 'APPMAIL_VALIDATE_ON_SAVE', True)
# used as the from_email address for sending emails
DEFAULT_SENDER = getattr(settings, 'APPMAIL_DEFAULT_SENDER', None)
# if True then add X-Appmail-* headers to outgoung email objects
ADD_EXTRA_HEADERS = getattr(settings, 'APPMAIL_ADD_HEADERS', True)
