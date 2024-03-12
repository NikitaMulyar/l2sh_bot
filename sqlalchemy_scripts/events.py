from datetime import datetime

import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Event(SqlAlchemyBase):
    __tablename__ = 'event'

    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    theme = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    date_start = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    date_end = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    place = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    edited = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True, default=datetime.now())
    status = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    file_path = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    # 0 - Скоро начнется; 1 - Идет; 2 - Недавно прошло (прошло не более 3 дней); -1 - В архиве

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.telegram_id"))
    user = orm.relationship("User")

    def __repr__(self):
        return f'<Event> {self.title}'
