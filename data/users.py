import sqlalchemy
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    chat_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, primary_key=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, primary_key=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    grade = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    number = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    choose_extra = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)

    def __repr__(self):
        return f'<User> {self.chat_id} {self.telegram_id}'
