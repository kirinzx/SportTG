import threading
from handlers import main
import sqlite3
from sportParser import Parser, channelsWorking
import asyncio


loop = asyncio.new_event_loop()

def startParsing():
    con = sqlite3.connect('bot.db')
    cur = con.cursor()
    for row in cur.execute("SELECT teamName, defaultName, channelID FROM channels;"):
        Parser(row[0],row[1],row[2],loop)
    con.close()

def createTables():
    con = sqlite3.connect('bot.db')
    cur = con.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY, teamName TEXT, defaultName TEXT ,channelID TEXT NOT NULL UNIQUE);'
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, nickname TEXT NOT NULL UNIQUE, adminId TEXT NOT NULL UNIQUE);"
    )
    con.commit()
    con.close()

def startBot():
    thread = threading.Thread(target=main,name="tgbot-thread",args=(loop,))
    thread.start()
    thread.join()


if __name__ == '__main__':
    createTables()
    startParsing()
    startBot()
    