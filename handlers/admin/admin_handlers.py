from asyncio import sleep
from datetime import datetime
from time import time

from aiogram import types
from aiogram.dispatcher import FSMContext

from config import ADMIN_ID, permissions_restrict, ADMIN_REPORT
from keyboard.default.menu import menu
from loader import dp, bot, lock
from utils import database
from utils.states import UpOneMonth, DownOneMonth, UserStatus

db = database.DBCommands()


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_REPORT),
                    commands=["start", "омощь"], commands_prefix=["/", "П"])
async def show_menu(message):
    markup = menu
    text = "Команды: \n\n<b>!+30</b> - продлить подписку на 30 дней \n<b>!-30</b> - уменьшить подписку на 30 дней" \
           "\n<b>?status</b> - посмотреть срок подписки" \
           "\n\n<b>Как пользоваться:</b> сообщение нужного пользователя <b>ПЕРЕСЛАТЬ</b> в группу " \
           "сопроводив соответствующей командой" \
           "\n\n\n\nЕщё команды: \n\n<b>!ban</b> - бан на сутки без продления подписки" \
           "\n\n<b>Как пользоваться: ОТВЕТИТЬ</b> на сообщение нужного пользователя в группе " \
           "сопроводив соответствующей командой"
    await message.answer(text=text, reply_markup=markup, parse_mode="HTML")


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["ban"], commands_prefix="!")
async def set_restrict(message: types.Message):
    if not message.reply_to_message:
        await message.delete()
        return

    chat_id = message.chat.id
    user_id = message.reply_to_message.from_user.id
    await message.delete()
    await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, until_date=time()+3600*24,
                                   permissions=permissions_restrict)

    name = message.reply_to_message.from_user.full_name
    await message.reply_to_message.reply(f"{name} ты забанен на сутки")


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["+30"], commands_prefix="!", state=None)
async def get_command_mess_id(message: types.Message, state: FSMContext):
    await UpOneMonth.mess_id.set()
    command_mess_id = message.message_id
    await state.update_data(id=command_mess_id)
    await message.delete()
    await sleep(1)
    await state.reset_state()


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["-30"], commands_prefix="!", state=None)
async def get_command_mess_id_down(message: types.Message, state: FSMContext):
    await DownOneMonth.mess_id.set()
    command_mess_id = message.message_id
    await state.update_data(id=command_mess_id)
    await message.delete()
    await sleep(1)
    await state.reset_state()


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["status"], commands_prefix="?", state=None)
async def get_command_mess_id_status(message: types.Message, state: FSMContext):
    await UserStatus.mess_id.set()
    command_mess_id = message.message_id
    await state.update_data(id=command_mess_id)
    await message.delete()
    await sleep(1)
    await state.reset_state()


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["+30"], commands_prefix="!", state="*")
async def reset_up(message: types.Message, state: FSMContext):
    await state.reset_state()
    await get_command_mess_id(message=message, state=state)


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["-30"], commands_prefix="!", state="*")
async def reset_down(message: types.Message, state: FSMContext):
    await state.reset_state()
    await get_command_mess_id_down(message=message, state=state)


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    commands=["status"], commands_prefix="?", state="*")
async def reset_status(message: types.Message, state: FSMContext):
    await state.reset_state()
    await get_command_mess_id_status(message=message, state=state)


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    is_forwarded=True, state=UpOneMonth.mess_id)
async def set_user_update_month(message: types.Message, state: FSMContext):
    data = await state.get_data()
    command_mess_id = data.get("id")
    current_mess_id = message.message_id
    timestamp = datetime.now().timestamp()
    referral = message.forward_from.id

    async with lock:
        await db.add_new_or_get_old_user_object(member=message.forward_from, timestamp=timestamp)

    if current_mess_id == command_mess_id+1:
        upd = await db.user_timestamp_update(referral=referral, timestamp=timestamp)
        upd_date = datetime.fromtimestamp(upd)
        name = message.forward_from.full_name
        group = message.chat.title
        text = f"Группа: <b>{group}</b> \nПользователь: <b>{name}</b> \n<b>ПРОДЛЕНА</b> подписка на 30 дней. \n" \
               f"Подписка до: <b>{upd_date.strftime('%d-%m-%Y %H:%M')}</b>"
        await bot.send_message(chat_id=ADMIN_REPORT, text=text, parse_mode="HTML")

    await state.reset_state()
    await message.delete()


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    is_forwarded=True, state=DownOneMonth.mess_id)
async def set_user_downgrade_month(message: types.Message, state: FSMContext):
    data = await state.get_data()
    command_mess_id = data.get("id")
    current_mess_id = message.message_id
    timestamp = datetime.now().timestamp()
    referral = message.forward_from.id

    async with lock:
        await db.add_new_or_get_old_user_object(member=message.forward_from, timestamp=timestamp)

    if current_mess_id == command_mess_id + 1:
        upd = await db.user_timestamp_downgrade(referral=referral, timestamp=timestamp)
        upd_date = datetime.fromtimestamp(upd)
        name = message.forward_from.full_name
        group = message.chat.title
        text = f"Группа: <b>{group}</b> \nПользователь: <b>{name}</b> \n<b>УМЕНЬШЕНА</b> подписка на 30 дней. \n" \
               f"Подписка до: <b>{upd_date.strftime('%d-%m-%Y %H:%M')}</b>"
        await bot.send_message(chat_id=ADMIN_REPORT, text=text, parse_mode="HTML")

    await state.reset_state()
    await message.delete()


def get_right_user(new_user, old_user):
    if new_user:
        return new_user
    elif old_user:
        return old_user


@dp.message_handler(lambda message: message.from_user.id == int(ADMIN_ID),
                    is_forwarded=True, state=UserStatus.mess_id)
async def get_user_status(message: types.Message, state: FSMContext):
    data = await state.get_data()
    command_mess_id = data.get("id")
    current_mess_id = message.message_id
    timestamp = datetime.now().timestamp()

    if current_mess_id == command_mess_id + 1:
        async with lock:
            new_user, old_user = await db.add_new_or_get_old_user_object(member=message.forward_from,
                                                                         timestamp=timestamp)
        user = get_right_user(new_user, old_user)
        name = message.forward_from.full_name
        group = message.chat.title
        timestamp_from_db = user.timestamp
        date = datetime.fromtimestamp(timestamp_from_db)
        text = f"Группа: <b>{group}</b> \nПользователь: <b>{name}</b> \n" \
               f"Подписка до: <b>{date.strftime('%d-%m-%Y %H:%M')}</b>"
        await bot.send_message(chat_id=ADMIN_REPORT, text=text, parse_mode="HTML")

    await state.reset_state()
    await message.delete()
