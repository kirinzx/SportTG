import asyncio
import threading
import requests
from datetime import datetime, timedelta
import schedule
import time
import configparser
from pytz import timezone
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from fake_useragent import UserAgent
from typing import List
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

class Parser:
    def __init__(self, teamName, defaultName, channelId, loop):
        self.loop = loop
        self.teamName = teamName
        self.defaultName = defaultName
        self.channelId = channelId
        ua = UserAgent()
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'uk,en-US;q=0.9,en;q=0.8,ru;q=0.7',
            'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': ua.random
        }
        self.scheduler = BackgroundScheduler()
        self.matches = []
        self.running = False
        self.thread = threading.Thread(target=self.startParsing,name=f'{teamName} main-thread_')
        self.thread.start()
    
    def startParsing(self):
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        channelsWorking.append(self)
        self.running = True
        self.scheduler.start()
        self.__setSchedule()
        

    def stop(self):
        self.scheduler.shutdown()
        self.running = False
        for i in range(len(channelsWorking)):
            if channelsWorking[i].channelId == self.channelId:
                del channelsWorking[i]
                break

    def __getLink(self,date=None):
        if not date:
            date = datetime.now(tz = timezone("Europe/Moscow")).strftime('%Y-%m-%d')
        return f'https://www.championat.com/stat/football/{date}.json'
    
    def __parsing(self):
        url = self.__getLink()
        response = requests.get(url,headers=self.headers)
        jsonResponse = response.json()
        tournaments = jsonResponse['matches']['football']['tournaments']

        for tournament,details in tournaments.items():
            matches = details['matches']
            for match in matches:
                if match['flags']['important'] == 1 and match['flags']['has_text_online'] == 1:
                    # and match['status']['label'] == 'dns'
                    teams = [team['name'] for team in match['teams']]
                    
                    if self.teamName in teams:
                        date = match["time_str"]
                        id = match['id']
                        nameToChange = f'СМОТРЕТЬ {teams[0].upper()} - {teams[1].upper()} Онлайн Прямая Трансляция'
                        date_obj = datetime.strptime(date, '%d.%m.%Y %H:%M')
                        
                        date_obj = date_obj - timedelta(minutes=float(self.__getSetting('timeToChange')))
                        if not id in self.matches:
                            self.__checkForDateChanges(nameToChange,date_obj,id,f'{teams[0].title()} - {teams[1].title()}')
                        

    def __checkForDateChanges(self,nameToChange,date,id,teams):
        self.matches.append(id)
        tz = timezone('Europe/Moscow')
        self.__changeName(nameToChange,id,teams)
        self.scheduler.add_job(self.__changeName, DateTrigger(run_date=date,timezone=tz),args=(nameToChange,id,teams),name=nameToChange)

    def __changeName(self,nameToChange,id=None,teams=None):
        if id:
            self.matches.remove(id)
        async def change():
            try:
                await bot.set_chat_title(chat_id=self.channelId,title=nameToChange)
                updates: List[types.Update] = await bot.get_updates(limit=1)
                nameChanged = updates[-1]
                await bot.delete_message(self.channelId,nameChanged.channel_post.message_id)
                if teams:
                    text = self.__getSetting('post').replace('$$',teams)
                    if text:
                        await bot.send_message(chat_id=self.channelId,text=text,parse_mode='HTML')
                
            except Exception as e:
                print(f'Error in {self.channelId}! {e}')
        self.loop.create_task(change())
        self.__checkIfOver(id)

    def __checkIfOver(self, id):
        url = self.__getLink()
        done = False
        while True:
            response = requests.get(url,headers=self.headers)
            jsonResponse = response.json()
            tournaments = jsonResponse['matches']['football']['tournaments']

            for tournament,details in tournaments.items():
                matches = details['matches']
                if done:
                    break
                for match in matches:
                    if id == match['id']:
                        if match['status']['label'] == 'fin':
                            self.__changeName(self.defaultName)
                            done = True
                            break
                
            if done:
                break
            time.sleep(120)

    def __getSetting(self, option: str) -> str:
        config = configparser.ConfigParser()
        config.read('settings.ini', encoding="utf-8")
        value = config.get('Settings',option)
        return value

    def __createThread(self):
        thread = threading.Thread(target=self.__parsing,name=f"{self.teamName} thread_")
        thread.start()

    def __setSchedule(self):
        self.__parsing()
        schedule.every(3).hours.do(self.__createThread)
        while True:
            schedule.run_pending()
            if not schedule.jobs:
                break
            if not self.running:
                break
            time.sleep(1)

channelsWorking : List[Parser] = []
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()

dp = Dispatcher(bot=bot,storage=storage)