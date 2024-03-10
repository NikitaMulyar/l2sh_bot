import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    chat_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, primary_key=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    telegram_tag = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    allow_changing = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True, default=False)
    role = sqlalchemy.Column(sqlalchemy.String, nullable=True, default="student")
    grade = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    number = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    choose_extra = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, default=0)
    extra_lessons = orm.relationship("Extra_to_User", backref="users")
    uid = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def __repr__(self):
        return f'<User> {self.chat_id} {self.telegram_id}'
