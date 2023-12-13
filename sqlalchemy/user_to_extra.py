import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from .users import *
from .extra_lessons import *


class Extra_to_User(SqlAlchemyBase):
    __tablename__ = 'extra_to_user'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.telegram_id"))
    extra_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("extra.id"))
