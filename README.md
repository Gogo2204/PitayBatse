# ПитайБаце

"ПитайБаце" е уеб приложение, в което регистриран потребител може да създава тикети за извършване на услуги по техния уебсайт, при заплащане на
съответната "Баце" такса. Тикетите се обработват от експерто пустиняци.

## Настройка за разработка

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

python manage.py migrate
```

## Създаване на суперпотребител

Суперадминът е обикновен Django суперпотребител (`is_superuser`), без отделна роля:

```bash
python manage.py createsuperuser
```

## Стартиране на сървъра

```bash
python manage.py runserver
```

## Автоматично връщане на неактивни тикети

Командата `check_inactive_tickets` намира тикетите в статус „Чакаме та“
(`waiting_reply`) или „Експерто бачка“ (`in_progress`), по които няма
активност от повече от `TICKET_INACTIVITY_HOURS` часа (по подразбиране 48),
и ги връща към статус „отворен“. Клиентът получава имейл, а промяната се
записва в лога като системно действие.

```bash
python manage.py check_inactive_tickets
```

Интервалът се настройва чрез `TICKET_INACTIVITY_HOURS` в настройките.

### Стартиране през cron

За да се изпълнява всеки час, добавете ред в crontab (`crontab -e`), като
използвате абсолютните пътища до виртуалната среда и проекта:

```cron
0 * * * * cd /path/to/pitaibace && /path/to/pitaibace/venv/bin/python manage.py check_inactive_tickets >> /var/log/pitaibace/inactive_tickets.log 2>&1
```

