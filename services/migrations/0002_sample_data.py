from django.db import migrations
from django.utils.text import slugify


DEPARTMENTS = [
    {
        "name": "Хостинг за сайто",
        "description": "Държим сайто буден и весел денонощно",
    },
    {
        "name": "Сигурност за сайто",
        "description": "Пазим сайто от лоши хора и бъгове",
    },
    {
        "name": "Дизайн за сайто",
        "description": "Правим сайто убаво да го гледаш",
    },
    {
        "name": "Интернет далавери",
        "description": "Уреждаме сайто в интернета, не питай как",
    },
]

SERVICES = [
    {
        "name": "Дезинфекция на сайто",
        "description": "Изтъркваме сайто до блясък от вируси и злина",
        "service_type": "one_time",
        "price": "149.99",
        "department": "Сигурност за сайто",
    },
    {
        "name": "Убав хостинг за сайто",
        "description": "Най-убавият хостинг, дето сайто ти е виждал",
        "service_type": "subscription",
        "price": "19.90",
        "department": "Хостинг за сайто",
    },
    {
        "name": "Спешна реанимация на сървъро",
        "description": "Сървъро падна? Ние го вдигаме, докато мигнеш",
        "service_type": "one_time",
        "price": "299.00",
        "department": "Хостинг за сайто",
    },
    {
        "name": "Лъскав дизайн за сайто",
        "description": "Правим сайто толкоз убав, че ще се разплачеш",
        "service_type": "one_time",
        "price": "499.50",
        "department": "Дизайн за сайто",
    },
    {
        "name": "Месечно глезене на сайто",
        "description": "Всеки месец пипаме, лъскаме и подмладяваме сайто",
        "service_type": "subscription",
        "price": "39.00",
        "department": "Хостинг за сайто",
    },
    {
        "name": "SEO по баровски",
        "description": "Качваме те първи в Гугъла, братле, имаме човек там",
        "service_type": "one_time",
        "price": "1337.99",
        "department": "Интернет далавери",
    },
]


def create_sample_data(apps, schema_editor):
    Department = apps.get_model("departments", "Department")
    Service = apps.get_model("services", "Service")

    departments = {}
    for data in DEPARTMENTS:
        department, _ = Department.objects.get_or_create(
            name=data["name"],
            defaults={
                "slug": slugify(data["name"], allow_unicode=True),
                "description": data["description"],
            },
        )
        departments[data["name"]] = department

    for data in SERVICES:
        Service.objects.get_or_create(
            name=data["name"],
            defaults={
                "description": data["description"],
                "service_type": data["service_type"],
                "price": data["price"],
                "department": departments[data["department"]],
                "is_active": True,
            },
        )


def remove_sample_data(apps, schema_editor):
    Department = apps.get_model("departments", "Department")
    Service = apps.get_model("services", "Service")

    Service.objects.filter(name__in=[s["name"] for s in SERVICES]).delete()
    Department.objects.filter(name__in=[d["name"] for d in DEPARTMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0001_initial"),
        ("departments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_sample_data, remove_sample_data),
    ]
