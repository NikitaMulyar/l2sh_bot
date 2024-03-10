import random

from sqlalchemy_scripts import db_session
from sqlalchemy_scripts.users import User


def create_uid(db_sess):
    s = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    uid = "".join([random.choice(s) for i in range(4)])
    res = db_sess.query(User).filter(User.uid == uid).first()
    while res:
        uid = "".join([random.choice(s) for i in range(4)])
        res = db_sess.query(User).filter(User.uid == uid).first()
    return uid


db_session.global_init("database/telegram_bot.db")
db_sess = db_session.create_session()
r = db_sess.query(User).all()
for el in r:
    el.uid = create_uid(db_sess)
db_sess.commit()
db_sess.close()
