import re
from asyncio import sleep

from datetime import datetime, timedelta

from aiogram import types
from aiogram.dispatcher.filters import IDFilter

from config import ADMIN_ID, CHAT_ID, NEED_USERS, SECONDS_TO_DEL
from handlers.admin.admin_handlers import get_right_user
from utils import database

from loader import dp, bot, lock, scheduler

db = database.DBCommands()


@dp.message_handler(IDFilter(chat_id=CHAT_ID), content_types=['new_chat_members'])
async def new_member(message: types.Message):
    referral = types.User.get_current().id
    chat_id = message.chat.id
    timestamp = datetime.now().timestamp()
    need_users = int(NEED_USERS)

    for member in message.new_chat_members:
        if member.is_bot:
            if referral != int(ADMIN_ID):
                member_id = member.id
                await bot.kick_chat_member(chat_id=chat_id, user_id=member_id)  # todo delete until_date
        elif referral != member.id:
            async with lock:
                await db.add_new_or_get_old_user_object(member=message.from_user, timestamp=timestamp)
            await db.referrer_update(need_users=need_users, referral=referral, timestamp=timestamp)
            async with lock:
                new_user, _ = await db.add_new_or_get_old_user_object(member=member,
                                                                      referral=referral,
                                                                      timestamp=timestamp)
            if new_user:
                await db.referrer_update(need_users=need_users, referral=referral, timestamp=timestamp)
        else:
            async with lock:
                await db.add_new_or_get_old_user_object(member=member, timestamp=timestamp)
    await message.delete()


@dp.message_handler(IDFilter(chat_id=CHAT_ID), content_types=['left_chat_member'])
async def left_member(message: types.Message):
    await message.delete()


@dp.message_handler(IDFilter(chat_id=CHAT_ID), lambda message: len(message.entities) > 0)
@dp.edited_message_handler(IDFilter(chat_id=CHAT_ID), lambda message: len(message.entities) > 0)
async def delete_links(message: types.Message):
    user_id = message.from_user.id
    for entity in message.entities:
        if entity.type in ["text_link"] and user_id != int(ADMIN_ID):
            await message.delete()
        elif entity.type in ["url"] and user_id != int(ADMIN_ID):
            re_string = r"chat.whatsapp|t.me/joinchat"
            text = message.text.lower()
            re_link = re.search(re_string, text)
            if re_link:
                await message.delete()
            else:
                await referral_control(message)
        else:
            await referral_control(message)


async def edit_restrict_message(message, name, number):
    ending = ["я", "ей"]
    if number == 1:
        end = ending[0]
    else:
        end = ending[1]
    text = f"{name}, \n\nдобавьте в группу \nещё {number} пользовател{end}, " \
           f"\nчтобы иметь возможность размещать объявления"
    restrict_message = await message.reply(
        text=text,
        allow_sending_without_reply=True
    )
    return restrict_message


async def schedule_message_to_delete(restrict_message):
    run_date = restrict_message.date + timedelta(seconds=int(SECONDS_TO_DEL))
    scheduler.add_job(restrict_message.delete, 'date', run_date=run_date)


@dp.message_handler(lambda message: message.from_user.id != int(ADMIN_ID),
                    IDFilter(chat_id=CHAT_ID), content_types=['any'])
async def referral_control(message: types.Message):
    user_id = types.User.get_current().id
    name = types.User.get_current().full_name
    timestamp = datetime.now().timestamp()
    need_users = int(NEED_USERS)

    if user_id != int(ADMIN_ID):
        async with lock:
            new_user, old_user = await db.add_new_or_get_old_user_object(member=message.from_user, timestamp=timestamp)
        db_user = get_right_user(new_user, old_user)
        if db_user.timestamp <= timestamp:
            number = need_users - db_user.referral_amount
            restrict_message = await edit_restrict_message(message=message, name=name, number=number)
            await message.delete()
            await schedule_message_to_delete(restrict_message)
        else:
            return
