import requests
from datetime import datetime
import schedule
import time

class Parser:
    def __init__(self, teamName, sport):
        self.teamName = teamName
        self.sport = sport
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
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
        }
    
    def start(self):
        self.__setSchedule()

    def stop(self):
        return schedule.CancelJob

    def __setLink(self):
        date = datetime.today().strftime('%Y-%m-%d')
        self.url = f'https://www.championat.com/stat/football/{date}.json'
    
    def __parsing(self):
        self.__setLink()
        #time MSK
        response = requests.get(self.url,headers=self.headers)
        jsonResponse = response.json()
        tournaments = jsonResponse['matches']['football']['tournaments']
        for tournament,details in tournaments.items():
            matches = details['matches']
            for match in matches:
                if match['flags']['important'] == 1 and match['flags']['has_text_online'] == 1:
                    teams = [team['name'] for team in match['teams']]
                    if self.teamName in teams:
                        print(teams[0] + ' - ' + teams[1])
                        #вызываем __checkForDateChanges()

    async def __checkForDateChanges(self):
        # если время подошло, то вызываем __changeName
        pass

    def __changeName(self):
        pass

    def __setSchedule(self):
        schedule.every(3).hours.do(self.__parsing)
        while True:
            schedule.run_pending()
            if not schedule.jobs:
                break
            time.sleep(1)

a = Parser('Динамо М','football')
a.parsing()


"""
    Расписание: 00:00, 04:00, 09:00, 12:00, 15:00, 18:00, 21:00
"""