import os
import logging
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'flowershop.settings'
django.setup()
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton,
    InlineKeyboardMarkup, KeyboardButton, LabeledPrice
)
from telegram.ext import (
    Updater, CommandHandler, ConversationHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext, PreCheckoutQueryHandler
)
from itertools import cycle
from environs import Env
from geopy.geocoders import Nominatim
from dateparser import parse
from datetime import datetime
from interface import (
    get_categories, get_bouquets_by_filter, get_catalog,
    get_user, add_user, get_bouquet_for_order, create_order
)

logger = logging.getLogger(__name__)

EVENT_BUTTONS = get_categories()

PRICE_BUTTONS = ['1000', '3000', '5000', '10000', 'Не важно']

OTHER_EVENT, PRICE = range(2)
USER_PHONE, USER_ADDRESS, USER_DELIVERY, SHOW_ORDER, ORDER_CONFIRM, START_PAYMENT = range(2, 8)
PHONE_NUMBER = 10

def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        if len(menu[-1]) == n_cols:
            menu.append([footer_buttons])
        else:
            menu[-1].append(footer_buttons)

    return menu


def start(update: Update, context: CallbackContext) -> int:

    EVENT_BUTTONS = get_categories()
    context.user_data['user'] = get_user(update.message.from_user.id)

    event_keyboard = build_menu(EVENT_BUTTONS, 2, footer_buttons='Другой повод')
    reply_markup = ReplyKeyboardMarkup(event_keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        text=(
            'К какому событию готовимся?\n'
            'Выберите один из вариантов:\n'
        ),
    reply_markup=reply_markup
    )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        text=(
            'До свидания, ждем следующего заказа.'
        ),
    reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def other_event(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        text=(
            'Введите свое событие:'
        ),
    )

    return OTHER_EVENT


def price_request(update: Update, context: CallbackContext) -> int:

    event = update.message.text
    context.user_data['event'] = event

    price_keyboard = build_menu(PRICE_BUTTONS, 3)
    reply_markup = ReplyKeyboardMarkup(price_keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        text=(
            'На какую сумму рассчитываете?'
        ),
    reply_markup=reply_markup
    )
    return PRICE


def show_relevant_flower(update: Update, context: CallbackContext) -> int:

    price = update.message.text
    context.user_data['price'] = price
    event = context.user_data.get('event')
    if price == 'Не важно':
        price = 100000
    bouquets = get_bouquets_by_filter(event, price)

    if bouquets:
        context.user_data['bouquets'] = cycle(bouquets)
        relevant_bouquet = bouquets[0]

        keyboard = [[InlineKeyboardButton('Заказать', callback_data=f'zakaz_{relevant_bouquet.id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_id = update.message.from_user.id
        update.effective_user.bot.send_photo(
            chat_id=user_id,
            photo= relevant_bouquet.img_url,
            caption=(
                f'{relevant_bouquet.name}\n\n'
                f'Описание: {relevant_bouquet.text}\n'
                f'Состав:\n {relevant_bouquet.content}\n\n'
                f'Цена: {relevant_bouquet.price}'
            ),
        reply_markup=reply_markup
        )
    else:
        bouquets = get_catalog()
        context.user_data['bouquets'] = cycle(bouquets)
        context.user_data['index'] = 0

        text='К сожалению в указанной категории нет букетов.'
        reply_markup = InlineKeyboardMarkup([])
        update.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )

    option_keyboard = [['Заказать консультацию', 'Посмотреть всю коллекцию']]
    reply_markup = ReplyKeyboardMarkup(option_keyboard, resize_keyboard=True)
    update.message.reply_text(
        text=(
            'Хотите что-то еще более уникальное?\n'
            'Подберите другой букет из нашей коллекции или закажите консультацию флориста.'
        ),
    reply_markup=reply_markup
    )

    return ConversationHandler.END

def show_catalog_flower(update: Update, context: CallbackContext) -> None:

    if context.user_data.get('bouquets'):
        for bouquet in context.user_data.get('bouquets'):
            new_bouquet = bouquet
            break

    keyboard = [[InlineKeyboardButton('Заказать', callback_data=f'zakaz_{new_bouquet.id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_id = update.message.from_user.id
    update.effective_user.bot.send_photo(
        chat_id=user_id,
        photo=new_bouquet.img_url,
        caption=(
            f'{new_bouquet.name}\n\n'
            f'Описание: {new_bouquet.text}\n\n'
            f'Состав:\n {new_bouquet.content}\n\n'
            f'Цена: {new_bouquet.price}'
        ),
        reply_markup=reply_markup
    )

    option_keyboard = [['Заказать консультацию', 'Посмотреть всю коллекцию']]
    reply_markup = ReplyKeyboardMarkup(option_keyboard, resize_keyboard=True)

    update.message.reply_text(
        text=(
            'Хотите что-то еще более уникальное?\n'
            'Подберите другой букет из нашей коллекции или закажите консультацию флориста.'
        ),
    reply_markup=reply_markup
    )


def phonenumber_request(update: Update, context: CallbackContext) -> int:

    if not context.user_data['user'] or update.message.text == 'Нет':
        keyboard = [[KeyboardButton('Отправить номер телефона', request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            text=(
                'Укажите номер телефона в формате 7ХХХХХХХХХХ, и наш флорист перезвонит вам в течение 20 минут.'
            ),
        reply_markup=reply_markup
        )
    else:
        option_keyboard = [['Да', 'Нет']]
        reply_markup = ReplyKeyboardMarkup(option_keyboard, resize_keyboard=True)

        update.message.reply_text(
            text=(
                f'Связаться с Вами можно по этому номеру: {context.user_data["user"].phone_number}?\n'
            ),
            reply_markup=reply_markup
        )

    return PHONE_NUMBER


def userphone_request(update: Update, context: CallbackContext) -> int:

    context.user_data['fullname'] = update.message.text

    if not context.user_data['user']:

        keyboard = [[KeyboardButton('Отправить номер телефона', request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            text=(
                'Укажите номер телефона в формате 7ХХХХХХХХХХ, и наш флорист перезвонит вам в течение 20 минут.'
            ),
        reply_markup=reply_markup
        )

    return USER_ADDRESS


def florist_answer(update: Update, context: CallbackContext) -> int:

    if not context.user_data['user']:
        phone_number = update.message.text
        if not phone_number:
            phone_number = update.message.contact.phone_number
        phone_number = phone_number.replace('+', '')
        add_user(tg_user_id=update.message.from_user.id, name='', phone_number=phone_number[1:])
        context.user_data['user'] = get_user(update.message.from_user.id)
    else:
        phone_number = context.user_data['user'].phone_number

    context.user_data['phone_number'] = phone_number

    event_keyboard = build_menu(EVENT_BUTTONS, 2, footer_buttons='Другой повод')
    reply_markup = ReplyKeyboardMarkup(event_keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        text=(
            'Флорист скоро свяжется с вами.'
            'А пока можете присмотреть что-нибудь из готовой коллекции.'
        ),
    reply_markup=reply_markup
    )

    # отправка уведомления флористу
    florist_id = context.bot_data['florist_id']
    user_data = context.user_data
    update.effective_user.bot.send_message(
        chat_id=florist_id,
        text=(
            'Заявка на обратный звонок для флориста!\n\n'
            f'Номер телефона: {phone_number}\n'
            f'Категория: {user_data["event"]}\n'
            f'Цена: {user_data["price"]}'
        ),
    )
    return ConversationHandler.END


def start_order_prepare(update: Update, context: CallbackContext):

    chat_id = update.message.chat_id
    context.user_data['id'] = chat_id
    user = context.user_data['user']

    if  user and user.name:

        keyboard = [[KeyboardButton('Отправить текущее местоположение', request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        update.effective_user.bot.send_message (
            chat_id=chat_id,
            text=(
                'Введите адрес доставки:'
            ),
            reply_markup=reply_markup
        )
        return USER_DELIVERY

    else:
        update.effective_user.bot.send_message(
            chat_id=chat_id,
            text=(
                'Введите ФИО:'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        return USER_PHONE


def address_request(update: Update, context: CallbackContext) -> int:

    phone_number = update.message.text
    if not phone_number:
        phone_number = update.message.contact.phone_number
    phone_number = phone_number.replace('+', '')

    context.user_data['phone_number'] = phone_number

    keyboard = [[KeyboardButton('Отправить текущее местоположение', request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        text=(
            'Введите адрес доставки:'
        ),
        reply_markup=reply_markup
    )

    return USER_DELIVERY


def datetime_request(update: Update, context: CallbackContext) -> int:

    if update.message.text:
        context.user_data['address'] = update.message.text
    else:

        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        geolocator = Nominatim(user_agent="flowers_bot")
        location = geolocator.reverse((latitude, longitude))
        context.user_data['address'] = location.address

    update.message.reply_text(
        text=(
            'Введите дату и время доставки:\n'
            '(в формате ДД.ММ.ГГГГ HH:MM)\n'
            'PS: можно и так: "завтра в 14:00" или "26 января"'
        ),
    )

    return SHOW_ORDER


def order_confirmation(update: Update, context: CallbackContext) -> int:

    delivery = update.message.text
    delivery = delivery.replace('-', ':')
    delivery_date_time = parse(delivery, languages=['ru',], settings={'PREFER_DATES_FROM': 'future'})
    if delivery_date_time:
        context.user_data['delivery'] = delivery_date_time
        date_delivery = context.user_data['delivery'].strftime('%d.%m.%Y')
        time_delivery = context.user_data['delivery'].strftime('%H:%M')
        if time_delivery == '00:00':
            time_delivery = 'Время уточнить'
    else:
        context.user_data['delivery'] = datetime.today()
        date_delivery = context.user_data['delivery'].strftime('%d.%m.%Y')
        time_delivery = 'Время уточнить'

    context.user_data['date_delivery'] = date_delivery
    context.user_data['time_delivery'] = time_delivery

    user = context.user_data['user']
    if user:
        context.user_data['phone_number'] = user.phone_number
    user_data = context.user_data

    option_keyboard = [['Да, все верно!', 'Я передумал']]
    reply_markup = ReplyKeyboardMarkup(option_keyboard, resize_keyboard=True)

    update.message.reply_text(
        text=(
            'Заявка на доставку!\n\n'
            f'Букет: {get_bouquet_for_order(user_data["bouquet_id"])}\n'
            f'Адрес: {user_data["address"]}\n'
            f'Дата и время доставки: {date_delivery} ({time_delivery})\n'
            f'Контактный телефон: {user_data["phone_number"]}'
        ),
    reply_markup=reply_markup
    )

    return ORDER_CONFIRM


def order_to_work(update: Update, context: CallbackContext) -> int:

    user_data = context.user_data
    user = context.user_data['user']

    if not get_user(tg_user_id=user_data['id']):
        add_user(tg_user_id=user_data['id'], name=user_data['fullname'], phone_number=user_data['phone_number'])

    order = create_order(user_data)
    if order:
        context.user_data['zakaz'] = order.id
    # отправка уведомления курьерам
    service_id = context.bot_data['service_id']
    user_data = context.user_data
    date_delivery = context.user_data['date_delivery']
    time_delivery = context.user_data['time_delivery']

    # отправка заявки на доставку в группу курьеров
    update.effective_user.bot.send_message(
        chat_id=service_id,
        text=(
            'Заявка на доставку!\n\n'
            f'Букет: {get_bouquet_for_order(user_data["bouquet_id"])}\n'
            f'Номер заказа: {order.id}\n'
            f'Адрес: {user_data["address"]}\n'
            f'Дата и время доставки: {date_delivery} ({time_delivery})\n'
            f'Контактный телефон: {user_data["phone_number"]}'
        ),
    )

    option_keyboard = [['Оплатить онлайн', 'Оплачу курьеру']]
    reply_markup = ReplyKeyboardMarkup(option_keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        text=(
            'Спасибо за Ваш заказ.\n'
            'Курьеры доставят его по указанному адресу в указанное Вами время.\n\n'
            'А пока Вы можете оплатить заказ онлайн!'
        ),
    reply_markup=reply_markup
    )

    return START_PAYMENT


def start_payment_callback(update: Update, context: CallbackContext) -> int:
    """Sends an invoice without shipping-payment."""
    chat_id = update.message.chat_id
    user_data = context.user_data
    payment_provider_token = context.bot_data['payment_provider_token']

    title = 'Payment Example'
    description = f'Оплата заказа № {user_data["zakaz"]}'
    # select a payload just for you to recognize its the donation from your bot
    payload = 'Custom-Payload'
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    currency = "RUB"
    # price in dollars
    bouquet = get_bouquet_for_order(user_data["bouquet_id"])
    price = 100 # int(bouquet.price)
    # price * 100 so as to include 2 decimal points
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    context.bot.send_invoice(
        chat_id, title, description, payload, payment_provider_token, currency, prices
    )

    return ConversationHandler.END


def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Custom-Payload':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


def successful_payment_callback(update: Update, context: CallbackContext) -> None:
        """Confirms the successful payment."""
        # do something after successfully receiving payment?
        update.message.reply_text("Thank you for your payment!")


def confirm_agreement(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    context.user_data['bouquet_id'] = query.data.split('_')[-1]

    context.user_data['id'] = update.effective_user.id

    agree_keyboard = [['Согласен', 'Не согласен']]
    reply_markup = ReplyKeyboardMarkup(agree_keyboard, resize_keyboard=True)

    update.effective_user.bot.send_document(
        chat_id=chat_id,
        document=open('soglasie.pdf', 'rb'),
        caption='Для оформления заказа требуется подтвердить согласие на обработку персональных данных',
        reply_markup=reply_markup
    )


if __name__ == '__main__':

    logger.setLevel(logging.INFO)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.info('Запущен FlowerShopBot')

    env = Env()
    env.read_env()
    bot_token = env.str("TG_TOKEN")
    florist_id = env('FLORIST_ID')
    service_id = env('SERVICE_ID')
    payment_provider_token = env('PAYMENT_PROVIDER_TOKEN')

    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    dispatcher.bot_data = {
        'florist_id': florist_id,
        'service_id': service_id,
        'payment_provider_token': payment_provider_token
    }

    other_event_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(Другой повод)$'), other_event)],
        states={
            OTHER_EVENT: [MessageHandler(Filters.text & (~Filters.command), price_request)
            ],
            PRICE: [
                MessageHandler(Filters.text(PRICE_BUTTONS), show_relevant_flower)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    order_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(Согласен)$'), start_order_prepare)],
        states={
            USER_PHONE: [
                MessageHandler(Filters.text & (~Filters.command), userphone_request)
            ],
            USER_ADDRESS: [
                # # regex номера телефона '^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'
                # # (Источник: https://habr.com/ru/post/110731/)
                MessageHandler(Filters.regex('^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'), address_request),
                MessageHandler(Filters.contact, address_request),
            ],
            USER_DELIVERY: [
                MessageHandler(Filters.text & (~Filters.command), datetime_request),
                MessageHandler(Filters.location, datetime_request),
            ],
            SHOW_ORDER: [
                MessageHandler(Filters.text & (~Filters.command), order_confirmation)
                ],
            ORDER_CONFIRM: [
                MessageHandler(Filters.regex('^(Да, все верно!)$'), order_to_work),
                MessageHandler(Filters.regex('^(Я передумал)$'), start)
                            ],
            START_PAYMENT: [
                MessageHandler(Filters.regex('^(Оплатить онлайн)$'), start_payment_callback),
                MessageHandler(Filters.regex('^(Оплачу курьеру)$'), cancel)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    florist_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(Заказать консультацию)$'), phonenumber_request)],
        states={
            PHONE_NUMBER: [
                MessageHandler(Filters.regex('^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'), florist_answer),
                MessageHandler(Filters.contact, florist_answer),
                MessageHandler(Filters.regex('^(Да)$'), florist_answer),
                MessageHandler(Filters.regex('^(Нет)$'), phonenumber_request)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text(EVENT_BUTTONS), price_request))
    dispatcher.add_handler(other_event_handler)
    dispatcher.add_handler(order_handler)
    dispatcher.add_handler(florist_handler)
    dispatcher.add_handler(MessageHandler(Filters.text(PRICE_BUTTONS), show_relevant_flower))
    dispatcher.add_handler(CallbackQueryHandler(confirm_agreement, pattern='^zakaz'))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(Посмотреть всю коллекцию)$'), show_catalog_flower))
    dispatcher.add_handler(MessageHandler(Filters.regex('^(Не согласен)$'), start))
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    updater.start_polling()
    updater.idle()
