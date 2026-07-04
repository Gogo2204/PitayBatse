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
