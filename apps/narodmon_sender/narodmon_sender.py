"""
ENG
AppDaemon narodmon.ru sender script
Credits: @Lefey / https://github.com/Lefey/ad_narodmon_sender
To enable this script add/edit parameters in /config/appdaemon/apps/narodmon_sender/config.yaml:
narodmon-sender:
  module: narodmon-sender
  class: narodmon-sender
  narodmon_device_mac: MAC-address to identify your device on narodmon.ru (mandatory)
  narodmon_device_name: Name for your device (optional)
  hass_coordinates_entity: Home assistant zone entity_id for getting latitude and longitude, helps auto placing device on map (optional)
  hass_sensor_entities: Comma-separated home assistant sensor entity_id`s, without spaces. Support sensor and binary_sensor domains (mandatory)
RU
AppDaemon скрипт для отправки данных на narodmon.ru
Автор: @Lefey / https://github.com/Lefey/ad_narodmon_sender
Для работы скрипта в AppDaemon необходимо прописать параметры в /config/appdaemon/apps/narodmon_sender/config.yaml:
narodmon-sender:
  module: narodmon-sender
  class: narodmon-sender
  narodmon_device_mac: MAC-адрес идентифицирующий ваше устройство на narodmon.ru, 12-18 символов A-Z и 0-9 без разделителей или разделенных '-' или ':' (обязательный параметр)
  narodmon_device_name: Имя вашего устройства (не обязательный параметр)
  hass_coordinates_entity: Зона home assistant для получения координат, для автоматического размещения устройства на карте (не обязательный параметр)
  hass_sensor_entities: Список cенсоров home assistant разделенный запятыми, без пробелов. Поддерживаются домены sensor и binary_sensor (обязательный параметр)

Example config / Пример конфигурации:
narodmon_sender:
  module: narodmon_sender
  class: narodmon_sender
  narodmon_device_mac: AABBCCDDEEFF
  narodmon_device_name: Xiaomi_WSDCGQ01LM
  hass_coordinates_entity: zone.home
  hass_sensor_entities: sensor.outside_temperature,sensor.outside_humidity,binary_sensor.door
"""
import appdaemon.plugins.hass.hassapi as hass
import socket
import datetime
import collections

class narodmon_sender(hass.Hass):
    #метод запускаемый однократно при старте программы
    def initialize(self):
        # объявляем переменные:
        # список сенсоров для отправки
        self.sensors = []
        # словарь имен для сенсоров (берем из friendly_name)
        self.sensors_name = {}
        # словарь типов сенсоров (берем из device_class, если есть)
        self.sensors_type = {}
        # форматированные данные для отправки
        self.device_data = None
        # словарь замены типов для автоопределения типа сенсора на narodmon.ru, 
        # исходные данные берутся из параметра device_class сенсора, при отсутстви датчики будут именованы как SENSOR#, тип нужно вручную определить на сайте.
        replace = {
            'temperature': 'TEMP',
            'humidity': 'RH',
            'pressure': 'PRESS',
            'battery': 'BATCHARGE',
            'power': 'W',
            'illuminance': 'LIGHT',
            'signal_strength': 'RSSI',
            None: 'SENSOR'
            }
        # проверяем, есть ли переменная с MAC-адресом в параметрах скрипта
        if 'narodmon_device_mac' in self.args:
            if self.args['narodmon_device_mac'] != None:
                # начинаем формировать данные для отправки
                self.device_data = '#' + self.args['narodmon_device_mac']
                # проверяем наличие названия устройства в параметрах скрипта, добавляем к MAC-адресу, если есть
                if 'narodmon_device_name' in self.args:
                    if self.args['narodmon_device_name'] != None:
                        self.device_data += '#' + self.args['narodmon_device_name']
                # проверяем наличие зоны в параметрах скрипта для определения координат
                if 'hass_coordinates_entity' in self.args:
                    if self.entity_exists(self.args['hass_coordinates_entity']):
                        lat = self.get_state(self.args['hass_coordinates_entity'], 'latitude')
                        lng = self.get_state(self.args['hass_coordinates_entity'], 'longitude')
                        if lat != None and lng != None:
                            self.device_data += '\n#LAT#' + str(lat) + '\n#LNG#' + str(lng)
            else:
                exit('Please, define narodmon_device_mac value in /config/appdaemon/apps/narodmon_sender/config.yaml')
        else:
            exit('Please, specify narodmon_device_mac variable in /config/appdaemon/apps/narodmon_sender/config.yaml')
        # проверка наличия перечня сенсоров в парамерах скрипта
        if 'hass_sensor_entities' in self.args:
            for entity in self.split_device_list(self.args['hass_sensor_entities']):
                # проверка существования объекта в home assistant
                if self.entity_exists(entity):
                    domain, sensor_id = self.split_entity(entity)
                    # отфильтровываем все кроме сенсоров и бинарных сенсоров
                    if domain == 'sensor' or domain == 'binary_sensor':
                        # заполняем список сенсоров для отправки
                        self.sensors.append(entity)
                        # заполняем словари имен и типов
                        self.sensors_name[entity] = self.get_state(entity, 'friendly_name')
                        self.sensors_type[entity] = self.get_state(entity, 'device_class')
            # на основе словаря типов переименовываем и нумеруем по порядку повторяющиеся
            for entity in self.sensors_type:
                if self.sensors_type[entity] in replace:
                    self.sensors_type[entity] = replace[self.sensors_type[entity]]
            count = collections.Counter(self.sensors_type.values())
            for type in count:
                if count[type] > 1:
                    num = count[type]
                    sel = 1
                    for entity in self.sensors_type:
                        if self.sensors_type[entity] == type:
                            self.sensors_type[entity] = type + str(range(num + 1)[sel])
                            sel = sel + 1
        else:
            exit('Please, specify hass_sensor_entities variable in /config/appdaemon/apps/narodmon_sender/config.yaml')
        # вызвываем метод отправки данных каждые 5 минут, начиная с текушего времени 
        self.run_every(self.send_data, datetime.datetime.now() + datetime.timedelta(seconds=2), 360)
    # метод для отправки данных
    def send_data(self, kwargs):
        binary_replace = {
            'off': '0',
            'on': '1'
            }
        sensors_data = '\n'
        # проверяем, есть ли сформированные данные об устройстве
        if self.device_data != None:
            for entity in self.sensors:
                # отбрасываем недоступные датчики
                if self.get_state(entity) != 'unavailable':
                    # замена состояния бинарных датчиков (on на 1 и off на 0), narodmon.ru не принимает в текстовом виде.
                    if self.get_state(entity) in binary_replace:
                        sensor_state = binary_replace[self.get_state(entity)]
                    else:
                        sensor_state = self.get_state(entity)
                # формируем строку с данными всех рабочих сенсоров
                sensors_data += '#' + self.sensors_type[entity] + '#' + sensor_state + '#' + self.sensors_name[entity] + '\n'
            # собираем пакет данных для отправки: информация об устройстве + данные сенсоров + символ окончания пакета данных
            data = self.device_data + sensors_data + '##'
            # вывод в лог информации которая будет отправлена
            self.log('Data for send to narodmon.ru:\n' + str(data))
            # создаем сокет для подключения к narodmon.ru
            sock = socket.socket()
            try:
                # пробуем подключиться
                sock.connect(('narodmon.ru', 8283))
                # пишем в сокет значения датчиков
                sock.send(data.encode('utf-8'))
                # читаем ответ сервера
                reply = str(sock.recv(1024))
                sock.close()
                self.log('Server reply: ' + reply.strip("bn\'\\"))
            except socket.error as err:
                self.error('Got error when connecting to narodmon.ru: ' + str(err))
        else:
            exit('No device data for send to narodmon.ru')
