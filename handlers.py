import threading
from aiogram import Dispatcher, executor, types, Bot
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import aiosqlite
import configparser
from middlewares import AdminMiddleware
from states import *
from paginator import Paginator
from sportParser import Parser, channelsWorking, bot, dp
import io

keyboardCancel = ReplyKeyboardMarkup(keyboard=[
    ["Отменить"],
])

keyboardMain = ReplyKeyboardMarkup(keyboard=[
    ['Добавить "админа"',"Добавить канал"],
    ["Как я работаю?"],
    ["Изменить время для переименовывания","Изменить шаблон для поста"],
    ['Посмотреть "админов"',"Посмотреть добавленные каналы"],
],resize_keyboard=True)

channelId = ''

@dp.message_handler(commands="start")
async def start(message: types.Message):
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding="utf-8")
    timeToChange = config.get('Settings','timeToChange')
    text = config.get('Settings','post')
    await message.answer(text=f"Выберите опцию. Выставленное время для переименовывания канала = {timeToChange} минут. Ваш пост выглядит так:\n{text}", reply_markup=keyboardMain,parse_mode='HTML')



@dp.message_handler(Text(equals='Отменить'), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Отменено', reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Как я работаю?'))
async def getHelp_handler(message: types.Message):
    await message.answer(text='Добавите меня в канал, дайте права менять описание канала. Потом зарегистрируйте этот канал здесь, нажав на кнопку "Добавить канал". После этого я буду менять его название в заданное время по заданным критериям',reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Посмотреть "админов"'))
async def getAdmins_handler(message: types.Message):
    async with aiosqlite.connect('bot.db')as db:
        async with db.execute("SELECT nickname,adminId FROM admins;")as cur:
            admins = await cur.fetchall()
    if len(admins) == 0:
        await message.answer(text='Админов нет...',reply_markup=keyboardMain)
    else:
        adminsButtons = InlineKeyboardMarkup()
        for admin in admins:
            if admin[1] == str(message.from_user.id):
                adminsButtons.add(InlineKeyboardButton(text=str(admin[0]), callback_data=f"view {admin[0]}"),
                                  InlineKeyboardButton(text=str(admin[1]), callback_data=f"view {admin[1]}"),
                                  InlineKeyboardButton(text="-", callback_data=f"fake-delete {admin[0]}"))
            else:
                adminsButtons.add(InlineKeyboardButton(text=str(admin[0]), callback_data=f"view {admin[0]}"),
                                  InlineKeyboardButton(text=str(admin[1]),callback_data=f"view {admin[1]}"),
                                  InlineKeyboardButton(text="Удалить", callback_data=f"delete admin {admin[0]}"))
        paginator = Paginator(adminsButtons, size=5, dp=dp)
        await message.answer(text="Добавленные админы",reply_markup=paginator())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete admin'))
async def process_callback_deleteAdmin(callback_query: types.CallbackQuery):
    adminToDelete = callback_query.data.split(" ")[-1]
    try:
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM admins WHERE nickname=?;", (adminToDelete,))
            await db.commit()

        await bot.send_message(callback_query.from_user.id, text=f"Готово! Админ {adminToDelete} удалён!",
                               reply_markup=keyboardMain)
    except:
        await bot.send_message(callback_query.from_user.id, text="Непридвиденная ошибка!", reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Посмотреть добавленные каналы'))
async def getChannels_handler(message: types.Message):
    async with aiosqlite.connect('bot.db')as db:
        async with db.execute("SELECT teamName,channelID FROM channels;")as cur:
            channels = await cur.fetchall()
    if len(channels) == 0:
        await message.answer(text='Каналов нет...',reply_markup=keyboardMain)
    else:
        channelButtons = InlineKeyboardMarkup()
        for channel in channels:
            channelButtons.add(InlineKeyboardButton(text=f'{channel[0]}', callback_data=f"view {channel[0]}"),
                                InlineKeyboardButton(text=f'{channel[1]}', callback_data=f"view {channel[1]}"),
                                InlineKeyboardButton(text="Изменить", callback_data=f"change channel {channel[1]}"))

        paginator = Paginator(channelButtons, size=8, dp=dp)
        await message.answer(text="Добавленные каналы",reply_markup=paginator())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change channel'))
async def process_callback_changeChannel(callback_query: types.CallbackQuery):
    channelId = callback_query.data.split(' ')[-1]
    newKeyboard = InlineKeyboardMarkup()
    isThere = False
    for channel in channelsWorking:
        if channel.channelId == channelId:
            isThere = True
            break
    if isThere:
        turn = InlineKeyboardButton(text='Стоп', callback_data=f'stop {channelId}')
    else:
        turn = InlineKeyboardButton(text='Пуск', callback_data=f'start {channelId}')
    delete = InlineKeyboardButton(text='Удалить',callback_data=f'delete {channelId}')
    changeTeam = InlineKeyboardButton(text='Сменить команду', callback_data=f'change team {channelId}')

    newKeyboard.add(turn,delete)
    newKeyboard.add(changeTeam)
    await callback_query.message.edit_text(text=f'ID просматриваемого канала: {channelId}')
    await callback_query.message.edit_reply_markup(newKeyboard)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('stop'))
async def process_callback_stopParsing(callback_query: types.CallbackQuery):
    channelId = callback_query.data.split(' ')[-1]
    for channel in channelsWorking:
        if channel.channelId == channelId:
            channel.stop()
            break
    await callback_query.message.delete()
    await bot.send_message(chat_id=callback_query.from_user.id,text='Готово!',reply_markup=keyboardMain)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('start'))
async def process_callback_startParsing(callback_query: types.CallbackQuery):
    channelId = callback_query.data.split(' ')[-1]
    async with aiosqlite.connect('bot.db')as db:
        async with db.execute(f'SELECT teamName, defaultName FROM channels WHERE channelId = {channelId};')as cur:
            data = await cur.fetchone()

        tmp = Parser(data[0], data[1], channelId,asyncio.get_event_loop())

    await callback_query.message.delete()
    await bot.send_message(chat_id=callback_query.from_user.id,text='Готово!',reply_markup=keyboardMain)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete'))
async def process_callback_deleteChannel(callback_query: types.CallbackQuery):
    channelId = callback_query.data.split(' ')[-1]
    
    async with aiosqlite.connect('bot.db')as db:
        await db.execute(f'DELETE FROM channels WHERE channelId = {channelId};')
        await db.commit()

    for channel in channelsWorking:
        if channel.channelId == channelId:
            channel.stop()
            break
    await callback_query.message.delete()
    await bot.send_message(chat_id=callback_query.from_user.id,text='Готово!',reply_markup=keyboardMain)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change team'))
async def process_callback_changeTeam(callback_query: types.CallbackQuery):
    global channelId
    channelId = callback_query.data.split(' ')[-1]
    await TeamNameForm.teamName.set()
    await callback_query.message.delete()
    await bot.send_message(chat_id=callback_query.from_user.id,text='Напишите название новой команды. Важно, чтобы название совпадало с названием на сайте https://www.championat.com/',reply_markup=keyboardCancel)
    
@dp.message_handler(state=TeamNameForm.teamName)
async def process_teamNameChange(message: types.Message, state: FSMContext):

    async with aiosqlite.connect('bot.db')as db:
        await db.execute(f'UPDATE channels SET teamName = ? WHERE channelId = ?;',(message.text.strip(),channelId))
        async with db.execute(f'SELECT teamName, defaultName FROM channels WHERE channelId = {channelId};')as cur:
            data = await cur.fetchone()
        await db.commit()
        

        tmp = Parser(data[0], data[1], channelId,asyncio.get_event_loop())

    for channel in channelsWorking:
        if channel.channelId == channelId:
            channel.stop()
            break
    await state.finish()
    await message.answer(text='Готово!',reply_markup=keyboardMain)


@dp.message_handler(Text(equals='Добавить "админа"'))
async def addAdmin(message:types.Message):
    await AdminForm.nickname.set()
    await message.answer("Напишите никнейм для этого аккаунта",reply_markup=keyboardCancel)

@dp.message_handler(state=AdminForm.nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['nickname'] = message.text.strip()
    await AdminForm.next()
    await message.reply("Напишите id аккаунта",reply_markup=keyboardCancel)

@dp.message_handler(state=AdminForm.adminId)
async def process_adminId(message:types.Message,state:FSMContext):
    async with state.proxy() as data:
        data['adminId'] = message.text.strip()

    async with aiosqlite.connect("bot.db")as db:
        try:
            if data["adminId"].isdigit():
                await db.execute("INSERT INTO admins(nickname,adminId) VALUES(?,?);",(data["nickname"],data["adminId"]))
                await db.commit()
                await state.finish()
                await message.reply("Готово!", reply_markup=keyboardMain)
            else:
                await message.reply("Некорректные данные!", reply_markup=keyboardMain)
        except aiosqlite.IntegrityError:
            await state.finish()
            await message.reply("Админ с такими данными уже сущетсвует!",reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Добавить канал'))
async def addChannel_handler(message: types.Message):
    await ChannelForm.teamName.set()
    await message.answer(text="Напишите, к какой команде привязать канал. Важно, чтобы название команды было таким же, как на сайте https://www.championat.com/",reply_markup=keyboardCancel)

@dp.message_handler(state=ChannelForm.teamName)
async def process_teamName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['teamName'] = message.text.strip()
    await ChannelForm.next()
    await message.answer(
        text='Напишите, на что менять название канала после окончания матча.',reply_markup=keyboardCancel
    )

@dp.message_handler(state=ChannelForm.defaultName)
async def process_defaultName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['defaultName'] = message.text.strip()
    await ChannelForm.next()
    await message.answer(text='Перешлите любой пост из канала',reply_markup=keyboardCancel)

@dp.message_handler(state=ChannelForm.channelId,content_types=types.ContentType.all())
async def process_channelId(message: types.Message, state: FSMContext):
    
    try:
        async with state.proxy() as data:
            teamName = data['teamName']
            defaultName = data['defaultName']
            channelId = str(message.forward_from_chat.id)
        async with aiosqlite.connect('bot.db')as db:
            await db.execute('INSERT INTO channels(teamName,defaultName,channelID) VALUES(?,?,?);',(teamName, defaultName, channelId))
            await db.commit()
        Parser(teamName, defaultName,channelId,asyncio.get_event_loop())
        await message.answer(text='Готово!',reply_markup=keyboardMain)
    except aiosqlite.IntegrityError:
        await message.answer(text='Канал с таким id уже зарегистрирован!',reply_markup=keyboardMain)
    except AttributeError:
        await message.answer(text='Ошибка! Что-то с вашим пересланным сообщением...',reply_markup=keyboardMain)
    finally:
        await state.finish()

@dp.message_handler(Text(equals='Изменить время для переименовывания'))
async def changeTimeToChange(message: types.Message):
    await TimeToChangeForm.timeToChange.set()
    await message.answer(text='Напиши время, которое нужно отнимать от времени матча, в минутах',reply_markup=keyboardCancel)

@dp.message_handler(state=TimeToChangeForm.timeToChange)
async def process_timeToChange(message: types.Message, state: FSMContext):
    value = message.text.strip()
    
    if value.isdigit():
        setSetting('timeToChange', value)
        await message.answer(text='Готово!',reply_markup=keyboardMain)
    else:
        await message.answer(text='Время должно быть числом!',reply_markup=keyboardMain)
    await state.finish()
    

@dp.message_handler(Text(equals='Изменить шаблон для поста'))
async def changePost(message: types.Message):
    await PostForm.post.set()
    await message.answer(text='Напишите желаемый шаблон для поста. Напишите $$ там, где нужно будет написать названия команд. Например, Смотреть $$. В итоге это получится: Смотреть Барселона - Ювентус(команды выбраны для примера)',reply_markup=keyboardCancel)

@dp.message_handler(state=PostForm.post,content_types=types.ContentType.all())
async def process_post(message: types.Message, state: FSMContext):
    
    
    if not '$$' in message.text.strip():
        await message.answer(text='Ошибка!Отсутствуют знаки $$',reply_markup=keyboardMain)
    else:
        try:
            config = configparser.ConfigParser()
            config.read('settings.ini', encoding="utf-8")
            if config.has_option('Settings','post'):
                setSetting('post',message.html_text)
            else:
                config['Settings']['post'] = message.html_text
                with open('settings.ini','w',encoding='utf-8')as config_file:
                    config.write(config_file)
            await message.answer(text='Готово!',reply_markup=keyboardMain)
        except Exception as e:
            await message.answer(text="Непридвиденная ошибка",reply_markup=keyboardMain)
            print(f"Error!{e}")
    await state.finish()

def setSetting(setting, value):
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding="utf-8")
    config.set('Settings',setting, value)
    with open('settings.ini','w',encoding='utf-8')as config_file:
        config.write(config_file)

def main(loop):
    asyncio.set_event_loop(loop)
    dp.middleware.setup(AdminMiddleware())
    executor.start_polling(dp, skip_updates=True,loop=loop)