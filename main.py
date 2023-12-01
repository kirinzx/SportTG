import threading
from handlers import main
import sqlite3
from sportParser import Parser
import asyncio
import logging

loop = asyncio.new_event_loop()
parser = Parser(loop)

def createTables():
    con = sqlite3.connect('bot.db')
    cur = con.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY, channelID TEXT NOT NULL UNIQUE, defaultName TEXT NOT NULL);'
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, nickname TEXT NOT NULL UNIQUE, adminId TEXT NOT NULL UNIQUE);"
    )
    con.commit()
    con.close()

def startBot():
    thread = threading.Thread(target=main,name="tgbot-thread",args=(loop,parser))
    thread.start()
    thread.join()


if __name__ == '__main__':
    #logging.basicConfig(level=logging.DEBUG)
    
    createTables()
    startBot()
    
    
    