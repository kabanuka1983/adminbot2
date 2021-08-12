import asyncio

from gino import Gino
from gino.schema import GinoSchemaVisitor
from sqlalchemy import (Column, Integer, BigInteger, String, Sequence, Float)
from sqlalchemy import sql

from config import DB_USER, DB_PASS, HOST

db = Gino()
lock = asyncio.Lock()


class User(db.Model):
    __tablename__ = 'users'
    query: sql.Select

    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    user_id = Column(BigInteger)
    full_name = Column(String(100))
    username = Column(String(50))
    referral = Column(Integer)
    referral_amount = Column(Integer)
    timestamp = Column(Float)

    def __repr__(self):
        return "<User(id='{}', fullname='{}', username='{}', timestamp='{}', referral_amount='{}')>".format(
            self.id, self.full_name, self.username, self.timestamp, self.referral_amount)


class DBCommands:

    @staticmethod
    async def get_user(user_id):
        user = await User.query.where(User.user_id == user_id).gino.first()
        return user

    async def add_new_or_get_old_user_object(self, member: User, timestamp, referral=None):
        user = member
        async with lock:
            old_user = await self.get_user(user.id)
        if old_user:
            return None, old_user
        new_user = User()
        new_user.user_id = user.id
        new_user.full_name = user.full_name
        new_user.username = user.username
        new_user.referral_amount = 0
        new_user.timestamp = timestamp

        if referral:
            new_user.referral = int(referral)
        await new_user.create()
        return new_user, None

    @staticmethod
    async def get_referral_amount(referral):
        amt = await db.select([db.func.count()]).where(User.referral == referral).gino.scalar()
        return amt

    async def referrer_update(self, need_users, referral, timestamp):
        amount = await self.get_referral_amount(referral=referral)
        new_amount = int(amount) % int(need_users)
        await User.update.values(referral_amount=new_amount).where(User.user_id == referral).gino.status()
        if amount > 0 and new_amount == 0:
            await self.user_timestamp_update(referral=referral, timestamp=timestamp)

    async def user_timestamp_update(self, referral, timestamp):
        db_user = await self.get_user(referral)
        if db_user.timestamp > timestamp:
            upd_timestamp = db_user.timestamp + 3600*24*30
        else:
            upd_timestamp = timestamp + 3600*24*30
        await User.update.values(timestamp=upd_timestamp).where(User.user_id == referral).gino.status()
        return upd_timestamp

    async def user_timestamp_downgrade(self, referral, timestamp):
        db_user = await self.get_user(referral)
        if db_user.timestamp > timestamp:
            upd_timestamp = db_user.timestamp - 3600*24*30
        else:
            upd_timestamp = db_user.timestamp
        await User.update.values(timestamp=upd_timestamp).where(User.user_id == referral).gino.status()
        return upd_timestamp


async def create_db():
    await db.set_bind(f'postgresql://{DB_USER}:{DB_PASS}@{HOST}/gino')

    db.gino: GinoSchemaVisitor
    await db.gino.drop_all() #todo delete
    await db.gino.create_all()