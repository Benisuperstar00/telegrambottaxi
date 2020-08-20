from datetime import datetime
import googlemaps
import polyline
import requests
import telebot
from django.conf import settings
from geopy import distance
from geopy.geocoders import Nominatim
from telebot import types
import time
import schedule
from telegrambot.models import Profile
from telegrambot.models import Trip

bot = telebot.TeleBot(token=settings.TOKEN)


@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id,
                     "Добро пожаловать, {0.first_name}!\nЯ - <b>{1.first_name}</b>, бот для вызова такси\n"
                     "Для старта бота отправьте /contact"
                     .format(message.from_user, bot.get_me()), parse_mode='html')


@bot.message_handler(commands=['info'])
def info(message):
    bot.send_message(message.chat.id,
                     "Я <b>{1.first_name}</b> был создан для того чтоб вы {0.first_name} могли вызвать такси.\n"
                     "Команды для работы со мной:\n"
                     "/start - Используется старта бота\n"
                     "/info ❓ - отправлю ещё раз это сообщение\n"
                     "/taxi 🚕 - вызов такси\n"
                     "/contact 📱 - отправка своей инфорации."
                     .format(message.from_user, bot.get_me()), parse_mode='html')


@bot.message_handler(commands=['taxi'])
def taxi(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text="Указать на карте 📍")
    button_text = types.KeyboardButton(text="Указать сообщением 📝")
    markup.add(button_geo, button_text)
    bot.send_message(message.chat.id,
                     '{0.first_name} Нажмите на кнопку 📍 для указание места посадки?'.format(message.from_user),
                     reply_markup=markup)
    bot.register_next_step_handler(message, start)  # следующий шаг – функция get_name


@bot.message_handler(commands=['contact'])
def com_contact(message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True,row_width=1, resize_keyboard=True)
    button_phone = types.KeyboardButton(text="📱", request_contact=True)
    keyboard.add(button_phone)
    bot.send_message(message.chat.id,
                     '{0.first_name} отправьте свой контакт нажав на кнопку 📱'.format(message.from_user),
                     reply_markup=keyboard)


@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact is not None:
        bot.send_message(message.chat.id,
                         f'Спасибо {message.from_user.first_name} {message.from_user.last_name}, за ваш номер телефона.\n'
                         f'Напишите /info для дополнительной информации')
        p, _ = Profile.objects.get_or_create(
            external_id=message.chat.id,
            name=message.chat.first_name,
            surname=message.chat.last_name,
            number=message.contact.phone_number,
        )
        return p


startAndEnd = {}


@bot.message_handler(content_types=['location'])
def location_medium(message):
    bot.send_message(message.from_user.id, 'Для вызова такси напишите /taxi')


@bot.message_handler(content_types=['text'])
def start(message):
    if message.text == 'Указать сообщением 📝':
        bot.send_message(message.from_user.id, "Укажите адрес где вы находитесь.")
        bot.register_next_step_handler(message, start_trip)
    elif message.text == 'Указать на карте 📍':
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_geo = types.KeyboardButton(text="Отправить своё местонахождение 📍", request_location=True)
        keyboard.add(button_geo)
        bot.send_message(message.from_user.id, "Отправь своё местонахождение через кнопку или через геопозицию",
                         reply_markup=keyboard)
        bot.register_next_step_handler(message, location)
    else:
        bot.send_message(message.from_user.id, 'Для вызова такси напишите /taxi')


global loc


def location(message):
    if message.location is not None:
        idMain = message.chat.id
        startAndEnd[str(idMain)] = []  # шаг 1 пустое значение
        lon = message.location.longitude
        lat = message.location.latitude
        ll = str(lat) + "," + str(lon)  # для геокодинга

        startAndEnd[str(idMain)].append(ll)  # шаг 2 точка старта

        zoom = 17  # Масштаб карты на старте. Изменяется от 1 до 19

        size = str(650) + "x" + str(450)
        markers = "color:red%7Clabel:A%7C" + startAndEnd[str(idMain)][0]
        map_request_a = "https://maps.googleapis.com/maps/api/staticmap?size={size}&zoom={z}&center={ll}&markers={markers}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
            ll=startAndEnd[str(idMain)][0], size=size, z=zoom, markers=markers)
        response = requests.get(map_request_a)
        map_file = "map.png"
        try:
            with open(map_file, "wb") as file:
                file.write(response.content)
        except IOError as ex:
            print("Ошибка записи временного файла:", ex)

        photo = open('map.png', 'rb')
        bot.send_photo(message.chat.id, photo)
        geolocator = Nominatim()
        loc = geolocator.reverse(startAndEnd[str(idMain)][0])
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True)
        button_geo_end = types.KeyboardButton(text="Указать на карте 📍")
        button_message = types.KeyboardButton(text="Указать сообщением 📝")
        button_end = types.KeyboardButton(text="Отменить поездку ❌")
        markup.add(button_geo_end, button_message, button_end)
        bot.send_message(message.chat.id,
                         f"Вы указали адрес посадки {loc.address}.\n"
                         f"Нажмите на кнопку Указать на карте 📍 чтоб указать конечный адрес на карте\n"
                         f"Нажмите на кнопку Указать сообщением 📝 \nчтоб указать конечный адрес cообщением\n"
                         f"Если вы передумали ехать нажмите кнопку Отменить поездку ❌", reply_markup=markup)
        bot.register_next_step_handler(message, location_medium)
    else:
        bot.send_message(message.from_user.id, 'Нажмите на кнопку')


# для сообщения
def start_trip(message):
    global markers
    idMain = message.chat.id
    grodno_address = "Гродно"
    loc = grodno_address + " " + message.text
    startAndEnd[str(idMain)] = []  # шаг 1 пустое значение
    geolocator = Nominatim(user_agent="benisuperstar")
    loc_to = geolocator.geocode(loc)
    ll = str(loc_to.latitude) + "," + str(loc_to.longitude)  # для геокодинга
    startAndEnd[str(idMain)].append(ll)  # шаг 2 точка старта
    zoom = 17  # Масштаб карты на старте. Изменяется от 1 до 19
    size = str(650) + "x" + str(450)
    markers = "color:red%7Clabel:A%7C" + startAndEnd[str(idMain)][0]
    map_request_a = "https://maps.googleapis.com/maps/api/staticmap?size={size}&zoom={z}&center={ll}&markers={markers}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
        ll=startAndEnd[str(idMain)][0], size=size, z=zoom, markers=markers)
    response = requests.get(map_request_a)
    map_file = "map.png"
    try:
        with open(map_file, "wb") as file:
            file.write(response.content)
    except IOError as ex:
        print("Ошибка записи временного файла:", ex)
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True)
    button_geo_end = types.KeyboardButton(text="Указать на карте 📍")
    button_message = types.KeyboardButton(text="Указать сообщением 📝")
    button_end = types.KeyboardButton(text="Отменить поездку ❌")
    markup.add(button_geo_end, button_message, button_end)

    photo = open('map.png', 'rb')
    bot.send_photo(message.chat.id, photo)
    bot.send_message(message.chat.id,
                     f'Вы указали адрес посадки {loc}')
    bot.send_message(message.chat.id,
                     f"Нажмите на кнопку Указать на карте 📍 чтоб указать конечный адрес на карте\n"
                     f"Нажмите на кнопку Указать сообщением 📝 чтоб указать конечный адрес cообщением\n"
                     f"Если вы передумали ехать нажмите кнопку Отменить поездку ❌", reply_markup=markup)
    bot.register_next_step_handler(message, location_medium)


def location_medium(message):
    if message.text == 'Указать на карте 📍':
        bot.send_message(message.from_user.id, "Отправь геолокацию ")
        bot.register_next_step_handler(message, location_end)  # следующий шаг – функция get_name
    if message.text == 'Указать сообщением 📝':
        bot.send_message(message.from_user.id, "Напишите адрес сообщением!")
        bot.register_next_step_handler(message, end_trip)  # следующий шаг – Конечная точка сообщением
    elif message.text == 'Отменить поездку ❌':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.from_user.id, 'Ваш заказ отмёнён!', reply_markup=markup)


######для локации
def location_end(message):
    if message.location is not None:
        idMain = message.chat.id
        # Получаем координаты для 2 точки
        lon_tho = message.location.longitude
        lan_tho = message.location.latitude
        lat_lon = str(lan_tho) + "," + str(lon_tho)  # для геокодинга
        startAndEnd[str(idMain)].append(lat_lon)  # шаг 2 точка старта
        zoom = 17  # Масштаб карты на старте. Изменяется от 1 до 19
        size = str(650) + "x" + str(450)
        markers_tho = "color:red%7Clabel:B%7C" + startAndEnd[str(idMain)][1]
        map_request_b = "https://maps.googleapis.com/maps/api/staticmap?size={size}&zoom={z}&center={ll}&markers={markers_tho}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
            ll=startAndEnd[str(idMain)][1], size=size, z=zoom,
            markers_tho=markers_tho)
        response_b = requests.get(map_request_b)
        map_file_tho = "map_tho.png"
        try:
            with open(map_file_tho, "wb") as file_tho:
                file_tho.write(response_b.content)
        except IOError as error:
            print("Ошибка записи временного файла:", error)

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True, )
        button_auto = types.KeyboardButton(text="Поиск машины")
        button_auto_exit = types.KeyboardButton(text="Отменить поездку")
        markup.add(button_auto, button_auto_exit)
        bot.send_message(message.chat.id, 'Нажмите поиск машины и ожидайте машину', reply_markup=markup)
        bot.register_next_step_handler(message, taxi_time)


def taxi_time(message):
    if message.text == 'Поиск машины':
        bot.send_message(message.chat.id, 'Мы ищем вам машину\n(примерное ожидание 2\мин)')
        schedule.every(1).minutes.do(taxi_autos, message).tag('daily-tasks')
        while True:  # Запуск цикла
            schedule.run_pending()
            time.sleep(1)
    elif message.text == "Отменить поездку":
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True, )
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.chat.id, 'Поездка отменена ', reply_markup=markup)



def taxi_autos(message):
    idMain = message.chat.id
    lat_auto = 53.678696
    lot_auto = 23.824667
    ll_auto = str(lat_auto) + "," + str(lot_auto)
    startAndEnd[str(idMain)].append(ll_auto)

    lat_auto_tho = 53.702092
    lot_auto_tho = 23.834161
    ll_auto_tho = str(lat_auto_tho) + "," + str(lot_auto_tho)
    startAndEnd[str(idMain)].append(ll_auto_tho)

    lat_auto_three = 53.688625
    lot_auto_three = 23.846140
    ll_auto_three = str(lat_auto_three) + "," + str(lot_auto_three)
    startAndEnd[str(idMain)].append(ll_auto_three)

    distance_trip_one = round(distance.distance(startAndEnd[str(idMain)][2], startAndEnd[str(idMain)][0]).km, 1)
    distance_trip_tho = round(distance.distance(startAndEnd[str(idMain)][3], startAndEnd[str(idMain)][0]).km, 1)
    distance_trip_trhee = round(distance.distance(startAndEnd[str(idMain)][4], startAndEnd[str(idMain)][0]).km, 1)
    list_distance = [distance_trip_one, distance_trip_tho, distance_trip_trhee]
    min_dist = min(list_distance)
    if distance_trip_one < distance_trip_tho and distance_trip_one < distance_trip_trhee:
        distance_taxi = startAndEnd[str(idMain)][2]
    elif distance_trip_tho < distance_trip_one and distance_trip_tho < distance_trip_trhee:
        distance_taxi = startAndEnd[str(idMain)][3]
    elif distance_trip_trhee < distance_trip_one and distance_trip_trhee < distance_trip_tho:
        distance_taxi = startAndEnd[str(idMain)][4]
    now = datetime.now()
    gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
    result = gmaps.directions(distance_taxi, startAndEnd[str(idMain)][0], mode="driving", departure_time=now)
    raw = result[0]['overview_polyline']['points']
    print(raw)
    points = polyline.decode(raw)
    pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
    path = "color:0xff0000ff |weight:5|" + pl
    size = str(650) + "x" + str(450)
    markers = "icon:https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/21/21b8051a22fb6c7c390d843fe04b6f5f1424f549_medium.jpg%7C" + distance_taxi
    map_request_tax = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
        size=size, markers=markers,
        markers_tho=startAndEnd[str(idMain)][0], path=path)
    response_tax = requests.get(map_request_tax)
    map_file_tax = "map_tax.png"
    try:
        with open(map_file_tax, "wb") as file_tax:
            file_tax.write(response_tax.content)
    except IOError as error:
        print("Ошибка записи временного файла:", error)

    taxi_time = round(min_dist / 0.6)
    photo_tax = open('map_tax.png', 'rb')
    bot.send_message(message.chat.id, f'Вам назначен автомобиль\n Приедет через:{taxi_time}/мин')

    bot.send_photo(message.chat.id, photo_tax)
    schedule.clear('daily-tasks')  # массовая отмена по тэгу
    schedule.every(taxi_time).minutes.do(taxi_run, message).tag('stop')
    while True:  # Запуск цикла
        schedule.run_pending()
        time.sleep(1)


def taxi_run(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = types.KeyboardButton(text="Ok")
    markup.add(button)
    schedule.clear('stop')
    bot.send_message(message.chat.id, "К вам подъехал автомобиль!!", reply_markup=markup)

    bot.register_next_step_handler(message, end_tripe_taxi)


def end_tripe_taxi(message):
    idMain = message.chat.id
    if message.text == 'Ok':
        now = datetime.now()
        markers_tho = "color:red%7Clabel:B%7C" + startAndEnd[str(idMain)][1]
        geolocator = Nominatim(user_agent="benisuperstar")
        gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
        result = gmaps.directions(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][1], mode="driving",
                                  departure_time=now)
        raw = result[0]['overview_polyline']['points']
        print(raw)
        points = polyline.decode(raw)
        pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
        path = "color:0xff0000ff |weight:5|" + pl
        size = str(650) + "x" + str(450)
        map_request_c = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
            size=size, markers=startAndEnd[str(idMain)][0],
            markers_tho=markers_tho, path=path)
        response_c = requests.get(map_request_c)
        map_file_c = "map_c.png"
        try:
            with open(map_file_c, "wb") as file_c:
                file_c.write(response_c.content)
        except IOError as error:
            print("Ошибка записи временного файла:", error)
        photo_c = open('map_c.png', 'rb')
        bot.send_photo(message.chat.id, photo_c)
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True)
        button_go = types.KeyboardButton(text="Поехали")
        button_dop = types.KeyboardButton(text="Дополнительная точка поездки")
        button_exit_dop = types.KeyboardButton(text="Отменить поездку ❌")
        markup.add(button_go, button_dop, button_exit_dop)
        distance_trip = round(distance.distance(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][1]).km, 1)
        loc = geolocator.reverse(startAndEnd[str(idMain)][0])
        loc_tho = geolocator.reverse(startAndEnd[str(idMain)][1])
        price = round(distance_trip)
        taxi_time = round(distance_trip / 0.6)
        if price < 1:
            price = 1
        bot.send_message(message.chat.id,
                         f'Ваш маршрут: {loc}\n'
                         f'===>{loc_tho.address}\n'
                         f'Расcтояние маршрута = {distance_trip}/км\n'
                         f'Стоимость поездки {price}Р\n'
                         f'Примерное время поездки {taxi_time} мин.\n'
                         f'Для начала поездки нажмите кнопку Поехали', reply_markup=markup)
        bot.register_next_step_handler(message, dop_start_medium)


def end_trip(message):
    global markers_tho, price
    global loc_tho
    idMain = message.chat.id
    groan_address = "Гродно"
    # trip_b= message.text
    geolocator = Nominatim(user_agent="benisuperstar")
    loc_tho = groan_address + " " + message.text
    # Получаем координаты для 2 точки
    loc_tho_chat = geolocator.geocode(loc_tho)
    lan_tho = loc_tho_chat.latitude
    lon_tho = loc_tho_chat.longitude
    lat_lon = str(lan_tho) + "," + str(lon_tho)  # для геокодинга
    startAndEnd[str(idMain)].append(lat_lon)  # шаг 2 точка старта
    zoom = 17  # Масштаб карты на старте. Изменяется от 1 до 19
    size = str(650) + "x" + str(450)
    markers_tho = "color:red%7Clabel:B%7C" + startAndEnd[str(idMain)][1]
    distance_trip = round(distance.distance(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][1]).km, 1)
    map_request_b = "https://maps.googleapis.com/maps/api/staticmap?size={size}&zoom={z}&center={ll}&markers={markers_tho}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
        ll=startAndEnd[str(idMain)][1], size=size, z=zoom,
        markers_tho=markers_tho)
    response_b = requests.get(map_request_b)
    map_file_tho = "map_tho.png"
    try:
        with open(map_file_tho, "wb") as file_tho:
            file_tho.write(response_b.content)
    except IOError as error:
        print("Ошибка записи временного файла:", error)
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True, )
    button_auto = types.KeyboardButton(text="Поиск машины")
    button_auto_exit = types.KeyboardButton(text="Отменить поездку")
    markup.add(button_auto, button_auto_exit)
    bot.send_message(message.chat.id, 'Нажмите поиск машины и ожидайте машину', reply_markup=markup)
    bot.register_next_step_handler(message, taxi_time_address)


def taxi_time_address(message):
    if message.text == 'Поиск машины':
        bot.send_message(message.chat.id, 'Мы ищем вам машину\n(примерное ожидание 2\мин) ')
        schedule.every(1).minutes.do(end_taxi_auto, message).tag('stop-tax')
        while True:  # Запуск цикла
            schedule.run_pending()
            time.sleep(1)
    elif message.text == "Отменить поездку":
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True, )
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.chat.id, 'Поездка отменена ', reply_markup=markup)


def end_taxi_auto(message):
    idMain = message.chat.id
    lat_auto = 53.678696
    lot_auto = 23.824667
    ll_auto = str(lat_auto) + "," + str(lot_auto)
    startAndEnd[str(idMain)].append(ll_auto)

    lat_auto_tho = 53.702092
    lot_auto_tho = 23.834161
    ll_auto_tho = str(lat_auto_tho) + "," + str(lot_auto_tho)
    startAndEnd[str(idMain)].append(ll_auto_tho)

    lat_auto_three = 53.688625
    lot_auto_three = 23.846140
    ll_auto_three = str(lat_auto_three) + "," + str(lot_auto_three)
    startAndEnd[str(idMain)].append(ll_auto_three)

    distance_trip_one = round(distance.distance(startAndEnd[str(idMain)][2], startAndEnd[str(idMain)][0]).km, 1)
    distance_trip_tho = round(distance.distance(startAndEnd[str(idMain)][3], startAndEnd[str(idMain)][0]).km, 1)
    distance_trip_trhee = round(distance.distance(startAndEnd[str(idMain)][4], startAndEnd[str(idMain)][0]).km, 1)
    list_distance = [distance_trip_one, distance_trip_tho, distance_trip_trhee]
    min_dist = min(list_distance)
    if distance_trip_one < distance_trip_tho and distance_trip_one < distance_trip_trhee:
        distance_taxi = startAndEnd[str(idMain)][2]
    elif distance_trip_tho < distance_trip_one and distance_trip_tho < distance_trip_trhee:
        distance_taxi = startAndEnd[str(idMain)][3]
    elif distance_trip_trhee < distance_trip_one and distance_trip_trhee < distance_trip_tho:
        distance_taxi = startAndEnd[str(idMain)][4]
    now = datetime.now()
    gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
    result = gmaps.directions(distance_taxi, startAndEnd[str(idMain)][0], mode="driving", departure_time=now)
    raw = result[0]['overview_polyline']['points']
    print(raw)
    points = polyline.decode(raw)
    pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
    path = "color:0xff0000ff |weight:5|" + pl
    size = str(650) + "x" + str(450)
    markers = "icon:https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/21/21b8051a22fb6c7c390d843fe04b6f5f1424f549_medium.jpg%7C" + distance_taxi
    map_request_tax = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
        size=size, markers=markers,
        markers_tho=startAndEnd[str(idMain)][0], path=path)
    response_tax = requests.get(map_request_tax)
    map_file_tax = "map_tax.png"
    try:
        with open(map_file_tax, "wb") as file_tax:
            file_tax.write(response_tax.content)
    except IOError as error:
        print("Ошибка записи временного файла:", error)

    taxi_time = round(min_dist / 0.6)
    photo_tax = open('map_tax.png', 'rb')
    bot.send_message(message.chat.id, f'Вам назначен автомобиль\n Приедет через:{taxi_time}/мин')

    bot.send_photo(message.chat.id, photo_tax)
    schedule.clear('stop-tax')  # массовая отмена по тэгу
    schedule.every(taxi_time).minutes.do(taxi_run_ex, message).tag('stop_taxi')
    while True:  # Запуск цикла
        schedule.run_pending()
        time.sleep(1)


def taxi_run_ex(message):
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = types.KeyboardButton(text="Okey")
    markup.add(button)
    bot.send_message(message.chat.id, "К вам подъехал автомобиль!!", reply_markup=markup)
    schedule.clear('stop_taxi')
    bot.register_next_step_handler(message, end_trip_tax)


def end_trip_tax(message):
    if message.text == "Okey":
        idMain = message.chat.id
        now = datetime.now()
        gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
        result = gmaps.directions(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][1], mode="driving",
                                  departure_time=now)
        raw = result[0]['overview_polyline']['points']
        points = polyline.decode(raw)
        pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
        path = "color:0xff0000ff |weight:5|" + pl
        size = str(650) + "x" + str(450)
        map_request_c = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
            size=size, markers=startAndEnd[str(idMain)][0],
            markers_tho=markers_tho, path=path)
        response_c = requests.get(map_request_c)
        map_file_c = "map_c.png"
        try:
            with open(map_file_c, "wb") as file_c:
                file_c.write(response_c.content)
        except IOError as error:
            print("Ошибка записи временного файла:", error)
        photo_c = open('map_c.png', 'rb')
        bot.send_photo(message.chat.id, photo_c)
        distance_trip = round(distance.distance(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][1]).km, 1)
        price = round(distance_trip)
        if price < 1:
            price = 1
        geolocator = Nominatim(user_agent="benisuperstar")
        loc = geolocator.reverse(startAndEnd[str(idMain)][0])
        taxi_time = round(distance_trip / 0.6)
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_dop = types.KeyboardButton(text="Дополнительная точка поездки")
        button_ok = types.KeyboardButton(text="Поехали")
        button_exit_dop = types.KeyboardButton(text="Отменить поездку ❌")
        markup.add(button_dop, button_ok, button_exit_dop)
        bot.send_message(message.chat.id,
                         f'Ваш маршрут:{loc}'
                         f'===>{loc_tho}\n'
                         f'Расcтояние маршрута = {distance_trip}/км\n'
                         f'Стоимость поездки: {price}P\n'
                         f'Примерное время поездки {taxi_time}/мин', reply_markup=markup)
        bot.register_next_step_handler(message, dop_start_medium)


def dop_start_medium(message):
    if message.text == 'Поехали':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_one = types.KeyboardButton(text="⭐")
        button_tho = types.KeyboardButton(text="⭐⭐")
        button_three = types.KeyboardButton(text="⭐⭐⭐")
        button_for = types.KeyboardButton(text="⭐⭐⭐⭐")
        button_five = types.KeyboardButton(text="⭐⭐⭐⭐⭐")
        markup.add(button_one, button_tho, button_three, button_for, button_five)
        bot.send_message(message.from_user.id, 'В конце поездки, выберите рейтинг поездки', reply_markup=markup)
        bot.register_next_step_handler(message, rating_taxi)

    elif message.text == 'Дополнительная точка поездки':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_geo_end = types.KeyboardButton(text="Указать на карте 📍")
        button_message = types.KeyboardButton(text="Указать сообщением 📝")
        button_end = types.KeyboardButton(text="Отменить поездку ❌")
        markup.add(button_geo_end, button_message, button_end)
        bot.send_message(message.from_user.id, "Выберите способ ввода дополнительной точки", reply_markup=markup)
        bot.register_next_step_handler(message, dop_start)
    elif message.text == 'Отменить поездку ❌':
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1, resize_keyboard=True)
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.from_user.id, 'Ваш заказ отмёнён!', reply_markup=markup)


def rating_taxi(message):
    print("dsadsadasd")
    idMain = message.chat.id
    geolocator = Nominatim(user_agent="benisuperstar")
    loc = geolocator.reverse(startAndEnd[str(idMain)][0])
    loc_tho = geolocator.reverse(startAndEnd[str(idMain)][1])
    if message.text == '⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            taxi_rate="1",
            profile=contact(message)
        )
    elif message.text == '⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            taxi_rate="2",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            taxi_rate="3",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            taxi_rate="4",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            taxi_rate="5",
            profile=contact(message)
        )
    markup = types.ReplyKeyboardMarkup(row_width=5, resize_keyboard=True)
    button_info = types.KeyboardButton(text="/info")
    markup.add(button_info)
    bot.send_message(message.from_user.id, 'Спасибо что указали рейтинг!',
                     reply_markup=markup)


def dop_start(message):
    if message.text == 'Указать на карте 📍':
        bot.send_message(message.from_user.id, "Отправь геолокацию ")
        bot.register_next_step_handler(message, location_point)
    if message.text == 'Указать сообщением 📝':
        bot.send_message(message.from_user.id, "Напишите адрес сообщением!")
        bot.register_next_step_handler(message, dop_trip)  # следующий шаг – Конечная точка сообщением
    elif message.text == 'Отменить поездку ❌':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.from_user.id, 'Ваш заказ отмёнён!', reply_markup=markup)


def location_point(message):
    if message.location is not None:
        idMain = message.chat.id
        geolocator = Nominatim(user_agent="benisuperstar")
        # Получаем координаты для дополнительной точки точки
        lon_tho = message.location.longitude
        lan_tho = message.location.latitude
        lat_lon_dop = str(lan_tho) + "," + str(lon_tho)  # для геокодинга
        loc_tho_dop = geolocator.reverse(lat_lon_dop)
        startAndEnd[str(idMain)].append(lat_lon_dop)  # шаг 2 точка старта
        size = str(650) + "x" + str(450)
        distance_trip_one = round(
            distance.distance(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][5]).km, 1)
        distance_trip_tho = round(distance.distance(startAndEnd[str(idMain)][5], startAndEnd[str(idMain)][1]).km, 1)
        distance_trip = distance_trip_one + distance_trip_tho
        now = datetime.now()
        gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
        result = gmaps.directions(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][5], mode="driving",
                                  departure_time=now)
        raw = result[0]['overview_polyline']['points']
        points = polyline.decode(raw)
        pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
        result_tho = gmaps.directions(startAndEnd[str(idMain)][5], startAndEnd[str(idMain)][1],
                                      mode="driving",
                                      departure_time=now)
        raw_tho = result_tho[0]['overview_polyline']['points']
        points_tho = polyline.decode(raw_tho)
        pl_tho = "|".join(["{0},{1}".format(p[0], p[1]) for p in points_tho])
        pl_general = pl + "|" + pl_tho
        path = "color:0xff0000ff |weight:5|" + pl_general
        map_request_dop = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&markers={markers_dop}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
            size=size,
            markers=startAndEnd[str(idMain)][0],
            markers_tho=startAndEnd[str(idMain)][1],
            markers_dop=startAndEnd[str(idMain)][5],
            path=path)
        price_loc = round(distance_trip, 1)
        if price_loc < 1:
            price_loc = 1
        taxi_time = round(distance_trip / 0.6)
        response_c = requests.get(map_request_dop)
        map_file_dop = "map_dop.png"
        try:
            with open(map_file_dop, "wb") as file_c:
                file_c.write(response_c.content)
        except IOError as error:
            print("Ошибка записи временного файла:", error)
        loc = geolocator.reverse(startAndEnd[str(idMain)][0])
        loc_tho = geolocator.reverse(startAndEnd[str(idMain)][1])
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_ok = types.KeyboardButton(text="Поехали")
        button_no = types.KeyboardButton(text="Отменить поездку ❌")
        markup.add(button_ok, button_no)
        photo_dop = open('map_dop.png', 'rb')
        bot.send_photo(message.chat.id, photo_dop)

        bot.send_message(message.chat.id,
                         f'Ваш маршрут перестроен:  {loc}\n'
                         f'===>{loc_tho_dop.address}\n'
                         f'===>{loc_tho}\n'
                         f'Расcтояние маршрута = {distance_trip}/км\n'
                         f'Стоимость поездки{price_loc}Р\n'
                         f'Примерное время поездки {taxi_time}/мин', reply_markup=markup)

        bot.register_next_step_handler(message, exit_trip)


def dop_trip(message):
    global price
    idMain = message.chat.id
    groan_address = "Гродно"
    geolocator = Nominatim(user_agent="benisuperstar")
    address_trip_dop = groan_address + " " + message.text
    # Получаем координаты для 2 точки
    loc_dop = geolocator.geocode(address_trip_dop)
    lan_dop = loc_dop.latitude
    lon_dop = loc_dop.longitude
    lat_dop = str(lan_dop) + "," + str(lon_dop)  # для геокодинга
    startAndEnd[str(idMain)].append(lat_dop)  # шаг 2 точка старта
    markers_dop = "color:red%7Clabel:B%7C" + startAndEnd[str(idMain)][5]
    size = str(650) + "x" + str(450)
    distance_trip_one = round(distance.distance(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][5]).km, 1)
    distance_trip_tho = round(distance.distance(startAndEnd[str(idMain)][5], startAndEnd[str(idMain)][1]).km, 1)
    distance_trip = round(distance_trip_one + distance_trip_tho)
    now = datetime.now()
    gmaps = googlemaps.Client(key='AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg')
    result = gmaps.directions(startAndEnd[str(idMain)][0], startAndEnd[str(idMain)][5], mode="driving",
                              departure_time=now)
    raw = result[0]['overview_polyline']['points']
    points = polyline.decode(raw)
    pl = "|".join(["{0},{1}".format(p[0], p[1]) for p in points])
    result_tho = gmaps.directions(startAndEnd[str(idMain)][5], startAndEnd[str(idMain)][1],
                                  mode="driving",
                                  departure_time=now)
    raw_tho = result_tho[0]['overview_polyline']['points']
    points_tho = polyline.decode(raw_tho)
    pl_tho = "|".join(["{0},{1}".format(p[0], p[1]) for p in points_tho])
    pl_general = pl + "|" + pl_tho
    path = "color:0xff0000ff |weight:5|" + pl_general
    map_request_c = "https://maps.googleapis.com/maps/api/staticmap?size={size}&markers={markers}&markers={markers_tho}&markers={markers_dop}&path={path}&key=AIzaSyC87S3ttehSCmIa76r7IE_omWk-3dEH1Rg".format(
        size=size, markers=startAndEnd[str(idMain)][0],
        markers_tho=markers_tho, path=path, markers_dop=markers_dop)
    response_c = requests.get(map_request_c)
    map_file_dop = "map_dop.png"
    try:
        with open(map_file_dop, "wb") as file_c:
            file_c.write(response_c.content)
    except IOError as error:
        print("Ошибка записи временного файла:", error)
    photo_dop = open('map_dop.png', 'rb')
    price = round(distance_trip)
    if price < 1:
        price = 1
    taxi_time = round(distance_trip / 0.6)
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_ok = types.KeyboardButton(text="Поехали")
    button_no = types.KeyboardButton(text="Отменить поездку ❌")
    loc = geolocator.reverse(startAndEnd[str(idMain)][0])
    loc_tho = geolocator.reverse(startAndEnd[str(idMain)][1])
    markup.add(button_ok, button_no)
    bot.send_photo(message.chat.id, photo_dop)
    bot.send_message(message.chat.id,
                     f'Ваш маршрут перестроен: {loc}\n'
                     f'===>{address_trip_dop}\n'
                     f'===>{loc_tho}\n'
                     f'Расcтояние маршрута = {distance_trip}/км\n'
                     f'Стоимость поездки: {price}\n'
                     f'Примерное время поездки {taxi_time}', reply_markup=markup)
    bot.register_next_step_handler(message, exit_trip)


def exit_trip(message):
    if message.text == 'Отменить поездку ❌':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_info = types.KeyboardButton(text="/info")
        markup.add(button_info)
        bot.send_message(message.from_user.id, 'Ваш заказ отмёнён!', reply_markup=markup)
    elif message.text == 'Поехали':
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_one = types.KeyboardButton(text="⭐")
        button_tho = types.KeyboardButton(text="⭐⭐")
        button_three = types.KeyboardButton(text="⭐⭐⭐")
        button_for = types.KeyboardButton(text="⭐⭐⭐⭐")
        button_five = types.KeyboardButton(text="⭐⭐⭐⭐⭐")
        markup.add(button_one, button_tho, button_three, button_for, button_five)
        bot.send_message(message.from_user.id, 'В конце поездки укажите рейтинг. Хорошей дороги!', reply_markup=markup)
        bot.register_next_step_handler(message, rate_taxi_end)


def rate_taxi_end(message):
    idMain = message.chat.id
    geolocator = Nominatim(user_agent="benisuperstar")
    loc = geolocator.reverse(startAndEnd[str(idMain)][0])
    loc_tho = geolocator.reverse(startAndEnd[str(idMain)][1])
    dop = geolocator.reverse(startAndEnd[str(idMain)][5])
    if message.text == '⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            dop_trip=dop,
            taxi_rate="1",
            profile=contact(message)
        )
    elif message.text == '⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            dop_trip=dop,
            taxi_rate="2",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            dop_trip=dop,
            taxi_rate="3",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            dop_trip=dop,
            taxi_rate="4",
            profile=contact(message)
        )
    elif message.text == '⭐⭐⭐⭐⭐':
        t, _ = Trip.objects.get_or_create(
            departure=loc,
            place_of_arrival=loc_tho,
            dop_trip=dop,
            taxi_rate="5",
            profile=contact(message)

        )
    elif message is not None:
        bot.send_message(message.chat.id, 'Укажите рейтинг!')

    markup = types.ReplyKeyboardMarkup(row_width=5, resize_keyboard=True)
    button_info = types.KeyboardButton(text="/info")
    markup.add(button_info)
    bot.send_message(message.from_user.id, 'Спасибо что указали рейтинг!',
                     reply_markup=markup)



# run
bot.polling(none_stop=True)
