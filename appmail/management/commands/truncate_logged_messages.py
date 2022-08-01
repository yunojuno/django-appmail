from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _lazy

from appmail.models import LoggedMessage
from appmail.settings import LOG_RETENTION_PERIOD


class Command(BaseCommand):

    help = _lazy("Truncate all log records that have passed the LOG_RETENTION_PERIOD.")

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "-r",
            "--retention",
            dest="retention",
            type=int,
            default=LOG_RETENTION_PERIOD,
            help="The number of days to retain logged messages.",
        )
        parser.add_argument(
            "-c",
            "--commit",
            dest="commit",
            action="store_true",
            default=False,
            help="If not set the transaction will be rolled back (no change).",
        )

    def get_logs(self, cutoff: date) -> QuerySet:
        """Return the queryset of logs to delete."""
        return LoggedMessage.objects.filter(timestamp__lt=cutoff)

    def cutoff(self, retention: int) -> date:
        """Return the date before which to truncate logs."""
        return date.today() - timedelta(days=retention)

    def handle(self, *args: Any, **options: Any) -> None:
        retention = options["retention"]
        commit = options["commit"]
        cutoff = self.cutoff(retention)
        self.stdout.write(f"Truncating records before {cutoff}")
        logs = self.get_logs(cutoff)
        self.stdout.write(f"Deleting {logs.count()} records")
        if not commit:
            self.stderr.write("Aborting transaction as --commit is False.")
            return
        count, _ = logs.delete()
        self.stdout.write(f"Deleted {count} records.")
        return
