# Телеграм-бот интернет-магазина по продаже букетов

Учебный проект имеет следующие возможности:
* Выбрать категорию букета, при необходимости указать свою категорию
* Выбрать ценовой диапазон
* Заказать консультацию флориста (Флористу в отдельную группу приходит заявка на консультацию)
* Выбрать другой букет из категории или общего каталога, если подобранный букет не нравится
* Сформировать заказ, указав при этом ФИО, номер телефона, адрес и дату доставки
* Для оформления заказа необходимо согласиться с "Согласием на обработку персональных данных"
* Возможность ввести адрес и телефон через стандартные функции ("Отправить номер телефона" и "Отправить геолокацию")
* После оформления заказа приходит сообщение в чат курьерам на доставку
* Добавлена возможность оплатить заказ онлайн в Телеграмм

База данных содержит информацию о Заказчиках, Букетах, Категориях и Заказах.  
База данных в проекте используется sqlite. Управление базой данных реализовано через `Django admin site`.

## Пример работы бота

![Чат-бот FlowersBot](https://github.com/kruser66/FlowerShopBot/blob/master/examples/bot_example.gif).


## Как установить

Скачайте код с репозитория.

Python3 должен быть уже установлен. Затем используйте pip (или pip3, если есть конфликт с Python2) для установки зависимостей:

```bash
pip install -r requirements.txt
```

### Переменные окружения

```
DEBUG=True  
DATABASE=sqlite:///db.sqlite3  
TG_TOKEN='Your bot token'  
FLORIST_ID='ChatID флористов'  
SERVICE_ID='ChatID курьеров'  
PAYMENT_PROVIDER_TOKEN = 'YOUR PAYMENT_PROVIDER_TOKEN'  
```

## Как запустить

Для работы Django можно использовать тестовую базу данных из папки  
[example](https://github.com/kruser66/FlowerShopBot/blob/master/examples/db.sqlite3)  
либо создать с нуля:

Создайте СуперПользователя для доступа в админку
```
python3 manage.py createsuperuser
```

Создайте миграции и примените миграции
```
python3 manage.py makemigrations
```
```
python3 manage.py migrate
```

#### Запустите локально сайт Django
```
python3 manage.py runserver
```
Доступ в админку будет по адресу: http://127.0.0.1:8000/admin/

#### Запустить чат-бот

```
python3 flowers_bot.py
```

# Цель проекта

Код написан в образовательных целях на онлайн-курс для веб-разработчиков [Devman](dvmn.org).
