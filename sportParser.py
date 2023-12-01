import asyncio
import json
import random
import threading
import requests
from datetime import datetime, timedelta
import schedule
import time
import configparser
from pytz import timezone
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job
from fake_useragent import UserAgent
from typing import List
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3
import os

class Match:
    channelId = None
    channelDefaultName = None
    def __init__(self, id, team1, team2, dateToChange: datetime, nameToChange, loop):
        self.id = id
        self.team1 = team1
        self.team2 = team2
        self.dateToChange = dateToChange
        self.nameToChange = nameToChange
        self.loop = loop
        self.message: types.Message | None = None
    
    def changeName(self, parser):
        print(f'changing {self.id}')
        async def change():
            @dp.channel_post_handler(lambda message: str(message.chat.id) == self.channelId,content_types=types.ContentType.NEW_CHAT_TITLE)
            async def tmp(message: types.Message):
                await message.delete()

            try:
                await bot.set_chat_title(chat_id=self.channelId,title=self.nameToChange)
            except Exception as e:
                print(f'Error in {self.id}date:{self.dateToChange.strftime("%d.%m.%Y %H:%M")}! {e}')

            try:
                await bot.set_chat_description(chat_id=self.channelId,description=f'Все матчи {self.team1.upper()} - {self.team2.upper()} можно БЕСПЛАТНО посмотреть здесь')
            except Exception as e:
                print(f'Error in desc!{e}')

            try:
                text = getSetting('post').replace('$$', self.team1.title() + ' - ' + self.team2.title())
                if text:
                    if os.path.isfile(os.path.join(os.getcwd(), 'videoToSend.mp4')):
                        with open('videoToSend.mp4','rb')as file:
                            self.message = await bot.send_video(chat_id=self.channelId,video=file,caption=text,parse_mode='HTML')
                    else:
                        self.message = await bot.send_message(chat_id=self.channelId,text=text,parse_mode='HTML',disable_web_page_preview=True)
            except Exception as e:
                print(f'Error in {self.id}date:{self.dateToChange.strftime("%d.%m.%Y %H:%M")}! {e}')

        self.loop.create_task(change())
        parser.checkIfOver(self)

    def end_match_actions(self):
        async def doStuff():
            try:
                if self.message:
                    await self.message.delete()
                    print(f'deleted {self.message.text}')
                else:
                    print(f'no message {self.nameToChange}')
            except Exception as e:
                print(f'error in end delete!{e}')
            try:
                if self.channelDefaultName:
                    await bot.set_chat_title(chat_id=self.channelId,title=self.channelDefaultName)
                else:
                    print(f'no channel default name in {self.id}')
                await bot.set_chat_description(chat_id=self.channelId,description=f'Все матчи можно БЕСПЛАТНО посмотреть здесь')
            except Exception as e:
                print(f'error in end title!{e}')
        self.loop.create_task(doStuff())
    
class Parser:
    def __init__(self, loop):
        self.loop = loop
        job_defaults = {
            'max_instances': 100,
            'coalesce': False,
        }
        self.scheduler = BackgroundScheduler(job_defaults=job_defaults)
        self.running = False
        self.event = threading.Event()
        self.tz = timezone('Europe/Moscow')
        self.matches = []
        self.thread = threading.Thread(target=self.startParsing,name='parser-thread')
        self.thread.start()
    
    def startParsing(self):
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        self.running = True
        self.scheduler.start()
        self.__setSchedule()
   

    def stop(self):
        self.scheduler.shutdown(wait=False)
        self.running = False

    def restart(self):
        self.scheduler.remove_all_jobs()
        self.matches = []
        self.__createThread()
    
    def __parsing(self):
        url = getLink()

        if url:
            try:
                response = makeRequest(url)
                jsonResponse = response.json()

                tournaments = jsonResponse['matches']['football']['tournaments']
                foundMatches = []
                for tournament,details in tournaments.items():
                    matches = details['matches']
                    for match in matches:
                        if match['flags']['important'] == 1 and match['flags']['has_text_online'] == 1 and match['status']['label'] == 'dns':
                            teams = [team['name'] for team in match['teams']]
                            date = match["time_str"]
                            id = match['id']
                            nameToChange = f'СМОТРЕТЬ {teams[0].upper()} - {teams[1].upper()} Онлайн Прямая Трансляция'
                            date_obj = datetime.strptime(date, '%d.%m.%Y %H:%M')
                            
                            date_obj = date_obj - timedelta(minutes=float(getSetting('timeToChange')))
                            
                            currentMatch = Match(id,teams[0],teams[1],date_obj,nameToChange,self.loop)
                            foundMatches.append(currentMatch)
            except Exception as e:
                print(f'Error in __parsing!{e}')


            if not len(foundMatches):
                return

            self.__distr(foundMatches)

    def __distr(self,foundMatches: List[Match]):
        """
        Распределение матчей
        """
        con = sqlite3.connect('bot.db')
        cur = con.cursor()
        cur.execute('SELECT channelId, defaultName FROM channels;')
        channels = cur.fetchall()
        con.close()
        foundMatchesCopy = foundMatches.copy()
        try:
            for item in range(len(foundMatchesCopy)):
                match = foundMatchesCopy[item]
                job: Job = self.scheduler.get_job(job_id=f'job_{match.id}')
                if job:
                    foundMatches.remove(match)
                    if job.next_run_time != match.dateToChange:
                        job.reschedule(DateTrigger(run_date=match.dateToChange,timezone=self.tz))
        except Exception as e:
            print(f'Error in __distr!{e}')
        while foundMatches:
            for channel in channels:
                if not foundMatches:
                    break
                try:
                    match = random.choice(foundMatches)
                    if not match.id in self.matches:
                        match.channelId = channel[0]
                        match.channelDefaultName = channel[1]
                        self.__addJob(match)
                    foundMatches.remove(match)
                except Exception as e:
                    print(f'Error in __distr in while!{e}')

    def __addJob(self,match: Match):
        print(f'added job {match.id}')
        self.matches.append(match.id)
        self.scheduler.add_job(match.changeName, DateTrigger(run_date=match.dateToChange,timezone=self.tz),args=(self,),id=f'job_{match.id}')
    

    def checkIfOver(self, targetMatch: Match):
        done = False
        while True:
            try:
                url = getLink()
                if url:
                    response = makeRequest(url)
                    jsonResponse = response.json()
                    tournaments = jsonResponse['matches']['football']['tournaments']

                    for tournament,details in tournaments.items():
                        matches = details['matches']
                        if done:
                            break
                        for match in matches:
                            if targetMatch.id == match['id']:
                                if match['status']['label'] == 'fin':
                                    done = True
                                    break
                    
                if done:
                    self.matches.remove(targetMatch.id)
                    targetMatch.end_match_actions()
                    break
                time.sleep(300)
            except Exception as e:
                print(f'Error in checkIfOver!{e}')
    

    def __createThread(self):
        thread = threading.Thread(target=self.__parsing)
        thread.start()

    def __setSchedule(self):
        self.__parsing()
        schedule.every(3).hours.do(self.__createThread)
        while True:
            schedule.run_pending()
            if self.event.is_set():
                self.restart()
                self.event.clear()
            if not schedule.jobs:
                break
            if not self.running:
                break
            time.sleep(1)

def getSetting(option: str) -> str:
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding="utf-8")
    value = config.get('Settings',option)
    return value

def makeRequest(url) -> requests.Response:
    ua = UserAgent()
    headers = {
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
    proxy = getSetting('proxy')
    if proxy:
        proxy = {
            'http': 'http://' + proxy,
            'https': 'http://' + proxy
        }
    else:
        proxy = None

    try:
        tmp = requests.get(url, headers=headers, proxies=proxy)
        tmpjs = tmp.json()
        return tmp
    except:
        tmp = requests.get(url, headers=headers)
        tmpjs = tmp.json()
        return tmp
    

def getLink():
    date = datetime.now(tz = timezone("Europe/Moscow")).strftime('%Y-%m-%d')
    tmp = makeRequest(f'https://www.championat.com/stat/data/{date}')
    try:
        jsonCheck = tmp.json()
        return f'https://www.championat.com/stat/data/{date}'
    except Exception as e:
        print(f"Error in getLink! {tmp.text}!{e}")
        return None

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot,storage=storage)