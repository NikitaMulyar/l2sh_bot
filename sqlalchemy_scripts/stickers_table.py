import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class Sticker(SqlAlchemyBase):
    __tablename__ = 'stickers'

    file_unique_id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    file_id = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def __repr__(self):
        return f'<Sticker> {self.file_id}'
