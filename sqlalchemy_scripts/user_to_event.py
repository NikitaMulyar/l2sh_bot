import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from .users import *
from .events import *


class Event_to_User(SqlAlchemyBase):
    __tablename__ = 'event_to_user'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.telegram_id"))
    event_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("event.id"))
