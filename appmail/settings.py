from django.conf import settings
from django.utils.module_loading import import_string

# Validate that EmailTemplate can be rendered without
# error on each save. Defaults to True.
VALIDATE_ON_SAVE = getattr(settings, "APPMAIL_VALIDATE_ON_SAVE", True)
# if True then add X-Appmail-* headers to outgoung email objects
ADD_EXTRA_HEADERS = getattr(settings, "APPMAIL_ADD_HEADERS", True)
# list of context processor functions applied on each render
CONTEXT_PROCESSORS = [
    import_string(s) for s in getattr(settings, "APPMAIL_CONTEXT_PROCESSORS", [])
]  # noqa

# If True then emails will be logged.
LOG_SENT_EMAILS = getattr(settings, "APPMAIL_LOG_SENT_EMAILS", True)

# The interval, in days, after which logs can be deleted
LOG_RETENTION_PERIOD = getattr(settings, "APPMAIL_LOG_RETENTION_PERIOD", 180)
