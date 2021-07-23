# import telebot
import requests
import re
import datetime
from time import sleep
import time
import os
import json
from telethon import TelegramClient, events
from config import *
import cv2


bot = TelegramClient('Bot', API_ID, API_HASH).start(bot_token=token)
bot.parse_mode = 'html'
def log(msg):
    message = '['+datetime.datetime.now().strftime('%d-%m-%Y * %H:%M:%S') + '] '+msg
    print( message )


def stat_img():
    """
    график сетевой активности из munin
    """
    url = munin_graph_url
    good = False
    try:
        data = requests.get(url)
        good = True
    except:
        good = False
    if good:
        f = open(r'stats.png','wb')
        f.write(data.content)
        f.close()
    return good

def cam_img():
    """
    Получение фото с камеры
    """
    result = False
    cap = cv2.VideoCapture(camera_stream_url)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite('cam.jpg',frame)
        result = True
    else:
        print('Can not capture')
        result = False
    cap.release()
    cv2.destroyAllWindows()
    return result

def update_vendor_base():
    """
    получение списка вендоров по мак адресу
    """
    vendor_list_url = 'http://standards-oui.ieee.org/oui/oui.txt'
    filename = 'vendor_macs.json'
    source_list = requests.get(vendor_list_url).text.split('\n')
    mac_vendors = {}
    for line in source_list:
        if 'base 16' in line:
            mac_vendors[line[:6]] = line.split('\t\t')[1]
    json.dump(mac_vendors,open(filename,'w'))

def get_vendor(mac):
    """
    получаем вендора по маку
    """
    filename = 'vendor_macs.json'
    search_mac = mac.upper().replace('-','').replace(':','')[:6]
    mac_vendors = {}

    if not os.path.exists(filename):
        update_vendor_base()
    mac_vendors = json.load( open(filename,'r'))

    if search_mac in mac_vendors:
        return mac_vendors[search_mac]
    else:
        return 'UNKNOWN VENDOR'

def GetOnline():    
    """
    Получаем список устройств с офисных роутеров
    """
    unknown = []
    
    now = time.time()
    mac_pattern = "'(([A-G0-9]{2}[:-]{0,1}){6})"
    mac_list = []
    try:
        log('Обращаемся к роутеру')
        r = requests.get(tplink_url, auth=tplink_auth)
        log('Получили код страницы')
        match = re.findall(r'..-..-..-..-..-..',r.text)
        if len(match) > 0:
            mac_list.extend(match)
    except:
        log('Роутер директоров недоступен')

    unknown = []

    for router in ddwrt_urls:
        wifi_url = f'{ddwrt_urls[router]}/Status_Wireless.live.asp'   

        try:
            r = requests.get(wifi_url, auth=ddwrt_auth, timeout = 10)
        except Exception as E:
            log (str(E))

        
        match = re.findall(mac_pattern,r.text.upper())
        if len(match) > 0:
            mac_list.extend( [mac[0].replace(':','-') for mac in match] )

        if len(mac_list) > 0:
            for mac in mac_list:
               if mac not in macs:
                   unknown.append('{} ( <b>{}</b> )'.format(mac, get_vendor(mac)))
    message = ''
    if len(mac_list) == 0:
        message = 'Никого в офисе нет :)\n'
    else:
        message = '<b>Сейчас в офисе:</b>\n'+'-  '*20
        known = [macs[i] for i in mac_list if i in macs]
        if len(known) > 0 : 
            message = message +'\n✅ '+ '\n✅ '.join(known)+'\n'
        if len(unknown)!=0:
            message = message + '\n<b>Неизвестные устройства:</b>\n'+'-  '*20+'\n❓ '+' \n❓ '.join(unknown)+'\n'
        diff = time.time() - now
    message = message + '-  '*20 + '\n<i>Запрос выполнен за {} мс</i>'.format(diff)
    r = ''
    return message

@bot.on(events.NewMessage(pattern='/in_office'))
async def in_office(event):
    """
    Отправляем список висящих на wifi в офисе по запросу
    """
    # tim = time.time()
    chatid =  event.chat_id
    # message_id = event.message.id
    sender = await event.get_sender()
    sender_id = sender.id
    message_text = event.message.message

    log ( f'Получено сообщение в телеграм от: {sender.username} , {sender_id} в чат  {chatid}' )

    while True:
        if chatid in chat_id_list:
            answer = GetOnline()
            await bot.send_message(chatid, answer)
            log ('Ответ на команду '+ message_text)
            log ( answer )
            break
        else:
            log('Chat_ID not in list')

@bot.on(events.NewMessage(pattern='/network_status'))
async def network_answer(event):
    """
    Отправляем график сетевой активности из munin по запросу
    """
    chatid =  event.chat_id
    message_id = event.message.id
    sender = await event.get_sender()
    message_text = event.message.message

    log ( f'Получено сообщение в телеграм от: {sender.username} , {sender.id} в чат  {chatid}' )
    good = stat_img()
    while True:
        if chatid in chat_id_list:
            if good:
                await bot.send_file(chatid,'stats.png',reply_to=message_id)
            else:
                await bot.send_message(chatid, 'График не получен')
            log ('Ответ на команду '+ message_text)
            break
        else:
            log('Chat_ID not in list')   

@bot.on(events.NewMessage(pattern='/camera'))
async def camera_answer(event):
    chatid =  event.chat_id
    message_id = event.message.id
    sender = await event.get_sender()
    message_text = event.message.message

    log ( f'Получено сообщение в телеграм от: {sender.username} , {sender.id} в чат  {chatid}' )
    good = cam_img()
    while True:
        if chatid in chat_id_list:
            if good:
                await bot.send_file(chatid,'cam.jpg',reply_to=message_id)
            else:
                await bot.send_message(chatid, 'Фото не получено')
            log ('Ответ на команду '+ message_text)
            break
        else:
            log('Chat_ID not in list')  

@bot.on(events.NewMessage)
async def received_message(event):
    chatid =  event.chat_id
    sender = await event.get_sender()
    message_text = event.message.message
    log(f'Получено сообщение от {sender.username} ({sender.id}) в чат  {chatid}')
    if 'писем нет' in message_text.lower():
        await bot.send_message(chatid, 'никто не пишет ..')

log('Стартуем')

while True:
    try:
        bot.run_until_disconnected()
        log('Телеграм не запустился')
        sleep(1)

    except :
        sleep(1)
        log('Error')


