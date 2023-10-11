# -*- coding: utf-8 -*-
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, Bot
import PyPDF2
from data.user_to_extra import Extra_to_User
from data.extra_lessons import Extra
from data import db_session
from data.users import User
from datetime import datetime, timedelta
from consts import *
import pandas as pd
import pdfplumber
import os
import shutil
import string
from config import *
import numpy as np


bot = Bot(BOT_TOKEN)


async def timetable_kbrd():
    btn = KeyboardButton('📚Расписание📚')
    btn2 = KeyboardButton('Расписание на день недели:')
    btn3 = KeyboardButton('🎨Мои кружки🎨')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn], [btn2], arr, [btn3]], resize_keyboard=True)
    return kbd


async def extra_school_timetable_kbrd():
    btn = KeyboardButton('♟️Сегодня♟️')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn], arr], resize_keyboard=True)
    return kbd


async def write_all(bot: telegram.Bot, text, all_=False, parse_mode=None):
    db_sess = db_session.create_session()
    all_users = db_sess.query(User).filter(User.grade != "АДМИН").all()
    if all_:
        all_users = db_sess.query(User).all()
    for user in all_users:
        try:
            if parse_mode:
                await bot.send_message(user.chat_id, text, parse_mode='MarkdownV2')
            else:
                await bot.send_message(user.chat_id, text)
        except Exception:
            pass


async def get_number_of_students_page_6_9(class_):
    if not os.path.exists(path_to_timetables + '6-9.pdf'):
        return -1
    reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
    page_n = 0
    for page in reader.pages:
        if class_ == page.extract_text().split('\n')[-1]:
            break
        page_n += 1
    else:
        # 'Такой класс не найден или для вашего класса нет расписания :('
        return -1
    return page_n


async def extract_timetable_for_day_6_9(day, pdf, page_n):
    if day == 6:
        day = 0
    table = pdf.pages[page_n].extract_table()
    df = pd.DataFrame(table[1:], columns=table[0])
    df[''].ffill(axis=0, inplace=True)
    day_num = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5}
    df[''] = df[''].apply(lambda x: day_num[x])
    for col in df.columns.values:
        if col != '':
            df[col] = df[col] + '###'
    df = df.groupby('').sum()
    for col in df.columns.values:
        df[col] = df[col].apply(lambda x: np.NaN if x == 0 else x)
    df = df.ffill(axis=1)
    df = df.iloc[day].to_frame()
    df[day] = df[day].str.strip('###')
    df[day] = df[day].apply(lambda x: np.NaN if x == '' else x)
    df.dropna(axis=0, inplace=True)
    return df, day


async def get_standard_timetable_for_user_6_9(class_, day):
    page_n = await get_number_of_students_page_6_9(class_)
    if page_n == -1:
        return pd.DataFrame(), page_n
    with pdfplumber.open(path_to_timetables + '6-9.pdf') as pdf:
        # day = (datetime.now() - timedelta(hours=3)).weekday()
        # !!!!!!!!!!!!!!!!!!!
        timetable_, day = await extract_timetable_for_day_6_9(day, pdf, page_n)
        return timetable_, day


async def get_timetable_for_user_6_9(context, class_):
    page_n = await get_number_of_students_page_6_9(class_)
    if page_n == -1:
        return pd.DataFrame(), page_n
    with pdfplumber.open(path_to_timetables + '6-9.pdf') as pdf:
        # day = (datetime.now() - timedelta(hours=3)).weekday()
        # !!!!!!!!!!!!!!!!!!!
        now_ = datetime.now()  # - timedelta(hours=3)
        day = now_.weekday()
        timetable_, day = await extract_timetable_for_day_6_9(day, pdf, page_n)
        last_les_end_h, last_les_end_m = map(int,
                                             timetable_.index.values[-1].split(' - ')[-1]
                                             .split(':'))
        # !!!!!!!!!!!!!!!!!!!!!
        h, m = now_.hour, now_.minute
        if (h, m) > (last_les_end_h, last_les_end_m):
            timetable_, day = await extract_timetable_for_day_6_9(day + 1, pdf, page_n)
            context.user_data['NEXT_DAY_TT'] = True
            # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
        else:
            context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


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


async def get_number_of_students_page(name, familia, class_):
    if not os.path.exists(path_to_timetables + class_):
        return -1
    reader = PyPDF2.PdfReader(path_to_timetables + class_)
    page_n = 0
    txt = familia.lower().capitalize() + ' ' + name.lower().capitalize()
    for page in reader.pages:
        if txt in page.extract_text():
            break
        page_n += 1
    else:
        # 'Такой ученик не найден или для вашего класса нет расписания :('
        return -1
    return page_n


async def get_standard_timetable_for_user(name, familia, class_, day):
    class_ = class_ + '.pdf'
    page_n = await get_number_of_students_page(name, familia, class_)
    if page_n == -1:
        return pd.DataFrame(), page_n
    with pdfplumber.open(path_to_timetables + class_) as pdf:
        # day = (datetime.now() - timedelta(hours=3)).weekday()
        # !!!!!!!!!!!!!!!!!!!
        timetable_, day = await extract_timetable_for_day(day, pdf, page_n)
        return timetable_, day


async def get_timetable_for_user(context, name, familia, class_):
    class_ = class_ + '.pdf'
    page_n = await get_number_of_students_page(name, familia, class_)
    if page_n == -1:
        return pd.DataFrame(), page_n
    with pdfplumber.open(path_to_timetables + class_) as pdf:
        # day = (datetime.now() - timedelta(hours=3)).weekday()
        # !!!!!!!!!!!!!!!!!!!
        now_ = datetime.now()  # - timedelta(hours=3)
        day = now_.weekday()
        timetable_, day = await extract_timetable_for_day(day, pdf, page_n)
        last_les_end_h, last_les_end_m = map(int,
                                             timetable_.index.values[-1].split(' - ')[-1]
                                             .split(':'))
        # !!!!!!!!!!!!!!!!!!!!!
        h, m = now_.hour, now_.minute
        if (h, m) > (last_les_end_h, last_les_end_m):
            timetable_, day = await extract_timetable_for_day(day + 1, pdf, page_n)
            context.user_data['NEXT_DAY_TT'] = True
            # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
        else:
            context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


"""async def clear_the_changes_folder():
    if os.path.exists(path_to_changes):
        shutil.rmtree(path_to_changes)
    os.mkdir(path_to_changes)"""


async def get_edits_in_timetable(next_day_tt):
    # filename format: DD.MM.YYYY
    time_ = datetime.now()
    day_ = str(time_.day).rjust(2, '0')
    month_ = str(time_.month).rjust(2, '0')
    today_file = f'{day_}.{month_}.{time_.year}.pdf'
    time_2 = time_ + timedelta(days=1)
    day_ = str(time_2.day).rjust(2, '0')
    month_ = str(time_2.month).rjust(2, '0')
    tomorrow_file = f'{day_}.{month_}.{time_2.year}.pdf'

    if len([i for i in os.walk(path_to_changes)][0][-1]) == 0:
        # Файла с изменениями нет
        return [], ''
    if next_day_tt:
        if not os.path.exists(path_to_changes + tomorrow_file):
            # Файла с изменениями нет
            return [], ''
    else:
        if not os.path.exists(path_to_changes + today_file):
            # Файла с изменениями нет
            return [], ''

    """period = (datetime(day=date_[0], month=date_[1], year=date_[2], hour=16, minute=30) - timedelta(days=1),
              datetime(day=date_[0], month=date_[1], year=date_[2], hour=16, minute=30))
    dfs = []
    if not period[0] < time_ < period[1]:
        # Изменения не актуальны
        return [], ''"""

    if not next_day_tt:
        day = "*Изменения на сегодня*"
        path_ = path_to_changes + tomorrow_file
    else:
        day = "*Изменения на завтра*"
        path_ = path_to_changes + tomorrow_file
    day = prepare_for_markdown('🔔') + day + prepare_for_markdown('🔔\n')
    dfs = []
    with pdfplumber.open(path_) as pdf:
        tables = []
        for page in pdf.pages:
            t = page.extract_tables()
            if len(t) == 1:
                tables.append(t[0])
            elif len(t) > 1:
                tables.extend(t)
        i = 1
        for table in tables:
            df = pd.DataFrame(table[1:], columns=table[0])
            df = df.fillna('')
            df = df.rename(columns={None: 'Замена2', 'Замена': 'Замены',
                                    'Замена кабинета': 'Замены кабинетов',
                                    "№\nурока": "№ урока",
                                    'Замена\nкабинета': 'Замены кабинетов',
                                    'Урок по\nрасписанию': 'Урок по расписанию'})
            if i == 1:
                df['Замены'] = df['Замены'] + '//' + df['Замена2']
                df.drop('Замена2', axis=1, inplace=True)
            i += 1
            dfs.append(df)
    return dfs, day


def prepare_for_markdown(text):
    res = ''
    for i in text:
        if i in string.punctuation:
            res += '\\' + i
        else:
            res += i
    return res


def put_to_db(update, name, surname, grade):
    db_sess = db_session.create_session()
    user__id = update.message.from_user.id
    num = grade
    if num != 'АДМИН':
        num = num[:-1]
    if db_sess.query(User).filter(User.telegram_id == user__id).first():
        if not db_sess.query(User).filter(User.telegram_id == user__id,
                                          User.chat_id == update.message.chat.id).first():
            user = User(chat_id=update.message.chat.id, telegram_id=user__id, surname=surname, name=name,
                        grade=grade, number=num)
            db_sess.add(user)
    else:
        user = User(chat_id=update.message.chat.id, telegram_id=user__id, surname=surname, name=name,
                    grade=grade, number=num)
        db_sess.add(user)
        db_sess.commit()
    db_sess.commit()
    db_sess.close()


def update_db(update, name, surname, grade):
    db_sess = db_session.create_session()
    user__id = update.message.from_user.id
    user = db_sess.query(User).filter(User.telegram_id == user__id).first()
    user.surname = surname
    user.name = name
    user.grade = grade
    user.number = grade[:-1]
    if grade == 'АДМИН':
        user.number = 'АДМИН'
    db_sess.commit()
    db_sess.close()


def extra_lessons_return(id, button_text):
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    db_sess = db_session.create_session()
    extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == id).all()
    text = ""
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text += extra.to_str()
    db_sess.close()
    return text
