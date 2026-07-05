import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from logs.models import ActivityLog
from orders.models import Order
from tickets.models import Attachment, Ticket

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Изтрива демо данните: тикети, поръчки, логове и всички потребители "
        "без суперпотребителите. Услугите и отделите остават непокътнати."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Пропуска интерактивното потвърждение (за скриптове).",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            answer = input(
                "Това ще изтрие всички тикети, поръчки, логове и потребители "
                "(без суперпотребителите). Продължи? [y/N] "
            )
            if answer.strip().lower() not in ("y", "yes"):
                self.stdout.write("Отказано.")
                return

        # Collect file paths before the rows are gone.
        file_paths = [a.file.path for a in Attachment.objects.all() if a.file]
        file_paths += [
            u.avatar.path
            for u in User.objects.filter(is_superuser=False)
            if u.avatar
        ]

        counts = {
            "Тикети": Ticket.objects.count(),
            "Поръчки": Order.objects.count(),
            "Логове": ActivityLog.objects.count(),
            "Потребители": User.objects.filter(is_superuser=False).count(),
        }

        with transaction.atomic():
            Ticket.objects.all().delete()
            Order.objects.all().delete()
            ActivityLog.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        removed_files = 0
        for path in file_paths:
            try:
                os.remove(path)
                removed_files += 1
            except FileNotFoundError:
                pass

        self.stdout.write(self.style.SUCCESS("Демо данните са изтрити:"))
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")
        self.stdout.write(f"  Изтрити файлове: {removed_files}")
