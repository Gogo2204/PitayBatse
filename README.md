# ПитайБаце

Тикет система, в която клиенти заплащат услуги за уебсайтове, а експерти
обработват тикетите.

## Настройка за разработка

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # попълнете SECRET_KEY, DEBUG и FERNET_KEY

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
