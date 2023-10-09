# -*- coding: utf-8 -*-
import telegram
import PyPDF2
from data import db_session
from data.users import User
from datetime import datetime
from consts import *
import pandas as pd
import pdfplumber
import os
import string


async def write_all(bot: telegram.Bot):
    db_sess = db_session.create_session()
    all_users = db_sess.query(User).all()
    for user in all_users:
        await bot.send_message(user.chat_id, 'Бот был перезапущен. '
                                             'Пожалуйста, заполните свои данные заново с помощью '
                                             'команды /start')


async def extract_timetable_for_day(day, pdf, page_n):
    if day == 6:
        day = 0
    page = pdf.pages[page_n]
    table = page.extract_table()
    df = pd.DataFrame(table[1:], columns=table[0])
    for col in df.columns.values:
        df.loc[df[col] == '', col] = '--'
    df.ffill(axis=1, inplace=True)
    df = df.iloc[day].to_frame()
    df = df[df[day] != '--'][day]
    return df, day


async def get_timetable_for_user(name, familia, class_):
    class_ = class_ + '.pdf'
    if not os.path.exists(path_to_timetables + class_):
        return pd.DataFrame(), -1
    reader = PyPDF2.PdfReader(path_to_timetables + class_)
    page_n = 0
    txt = familia.lower().capitalize() + ' ' + name.lower().capitalize()
    for page in reader.pages:
        if txt in page.extract_text():
            break
        page_n += 1
    else:
        # 'Такой ученик не найден или для вашего класса нет расписания :('
        return pd.DataFrame(), -1
    with pdfplumber.open(path_to_timetables + class_) as pdf:
        day = datetime.now().weekday()
        timetable_, day = await extract_timetable_for_day(day, pdf, page_n)
        last_les_end_h, last_les_end_m = map(int,
                                             timetable_.index.values[-1].split(' - ')[-1]
                                             .split(':'))
        now_ = datetime.now()
        h, m = now_.hour, now_.minute
        if (h, m) > (last_les_end_h, last_les_end_m):
            timetable_, day = await extract_timetable_for_day(day + 1, pdf, page_n)
    return timetable_, day


def prepare_for_markdown(text):
    res = ''
    for i in text:
        if i in string.punctuation:
            res += '\\' + i
        else:
            res += i
    return res


def put_to_db(update):
    db_sess = db_session.create_session()
    user__id = update.message.from_user.id
    message__id = update.message.chat.id
    if db_sess.query(User).filter(User.chat_id == message__id).first():
        if not db_sess.query(User).filter(User.telegram_id == user__id,
                                          User.chat_id == message__id).first():
            user = User(chat_id=message__id, telegram_id=user__id)
            db_sess.add(user)
    else:
        user = User(chat_id=message__id, telegram_id=user__id)
        db_sess.add(user)
        db_sess.commit()
    db_sess.commit()
    db_sess.close()
