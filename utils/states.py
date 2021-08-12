from aiogram.dispatcher.filters.state import StatesGroup, State


class UpOneMonth(StatesGroup):
    mess_id = State()


class DownOneMonth(StatesGroup):
    mess_id = State()


class UserStatus(StatesGroup):
    mess_id = State()
