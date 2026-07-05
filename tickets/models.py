import uuid

from django.conf import settings
from django.db import models

from .fields import EncryptedTextField


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Баце, ке го видим"
        IN_PROGRESS = "in_progress", "Експерто бачка"
        WAITING_REPLY = "waiting_reply", "Чекаме та"
        CLIENT_REPLIED = "client_replied", "Има отговор, баце"
        RESOLVED = "resolved", "Оправено е, баце"

    class Priority(models.TextChoices):
        LOW = "low", "Мани, че почека"
        NORMAL = "normal", "Кога можеш, баце"
        HIGH = "high", "Тичай, че гори!"

    public_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    site_url = models.URLField(
        blank=True,
        default="",
        verbose_name="Сайт",
        help_text="Адресът на сайта, за който е тикетът",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    main_expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_tickets",
    )
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="watched_tickets",
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.public_id})"

    @property
    def short_code(self):
        return self.public_id.hex[:8].upper()


class Message(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Съобщение #{self.pk}"


class Attachment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="tickets/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class Credential(models.Model):
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="credential",
    )
    site_admin_url = models.URLField(blank=True)
    site_username = EncryptedTextField(blank=True)
    site_password = EncryptedTextField(blank=True)
    hosting_username = EncryptedTextField(blank=True)
    hosting_password = EncryptedTextField(blank=True)

    def __str__(self):
        return f"Тайни за тикет #{self.ticket_id}"
