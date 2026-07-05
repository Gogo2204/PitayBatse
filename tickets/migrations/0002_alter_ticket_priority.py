from django.db import migrations, models


def remap_urgent_to_high(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    Ticket.objects.filter(priority="urgent").update(priority="high")


def reverse_noop(apps, schema_editor):
    # Reversing cannot restore which tickets were originally "urgent".
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remap_urgent_to_high, reverse_noop),
        migrations.AlterField(
            model_name='ticket',
            name='priority',
            field=models.CharField(choices=[('low', 'Мани, че почека'), ('normal', 'Кога можеш, бате'), ('high', 'Тичай, че гори!')], default='normal', max_length=20),
        ),
    ]
