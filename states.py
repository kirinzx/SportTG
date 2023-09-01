from aiogram.dispatcher.filters.state import State, StatesGroup

class AdminForm(StatesGroup):
    nickname = State()
    adminId = State()

class ChannelForm(StatesGroup):
    teamName = State()
    defaultName = State()
    channelId = State()

class TeamNameForm(StatesGroup):
    teamName = State()

class TimeToChangeForm(StatesGroup):
    timeToChange = State()

class PostForm(StatesGroup):
    post = State()