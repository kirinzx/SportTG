from aiogram.dispatcher.filters.state import State, StatesGroup

class AdminForm(StatesGroup):
    nickname = State()
    adminId = State()

class ChannelForm(StatesGroup):
    channelId = State()
    defaultName = State()

class TimeToChangeForm(StatesGroup):
    timeToChange = State()

class PostForm(StatesGroup):
    post = State()

class VideoForm(StatesGroup):
    video = State()

class ProxyForm(StatesGroup):
    proxy = State()