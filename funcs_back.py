# -*- coding: utf-8 -*-
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, Bot
from data.user_to_extra import Extra_to_User
from data.extra_lessons import Extra
from data import db_session
from data.users import User
from datetime import datetime, timedelta
from timetables_csv import *
import string
from config import *
import numpy as np
import asyncio


db_session.global_init("database/telegram_bot.db")
bot = Bot(BOT_TOKEN)
db_sess = db_session.create_session()


def throttle(func):
    def wrapper(*args, **kwargs):
        now_ = datetime.now()
        last_time = args[2].user_data.get('last_time')
        if not last_time:
            args[2].user_data['last_time'] = now_
            asyncio.gather(func(*args, **kwargs))
        elif last_time + timedelta(seconds=0.5) <= now_:
            args[2].user_data['last_time'] = now_
            asyncio.gather(func(*args, **kwargs))
        else:
            asyncio.gather(trottle_ans(*args, **kwargs))
    return wrapper


async def trottle_ans(*args, **kwargs):
    await args[1].message.reply_text('🧨 Воу-воу, помедленнее! Ты Молния Маквин что-ли?')


async def timetable_kbrd():
    btn = KeyboardButton('📚Расписание📚')
    btn2 = KeyboardButton('Расписание на день недели:')
    btn3 = KeyboardButton('🎨Мои кружки🎨')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn], [btn2], arr, [btn3]], resize_keyboard=True)
    return kbd


async def extra_school_timetable_kbrd():
    btn = KeyboardButton('♟️Сегодня♟️')
    btn2 = KeyboardButton('🎭Все кружки🎭')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn, btn2], arr], resize_keyboard=True)
    return kbd


async def write_all(bot: telegram.Bot, text, all_=False, parse_mode=None):
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


async def extract_timetable_for_day_6_9(day, class_):
    df = pd.read_csv(path_to_timetables_csv + f'{class_}.csv')
    df = df.iloc[day].to_frame()
    df[day] = df[day].str.strip('###')
    df[day] = df[day].apply(lambda x: np.NaN if x == '' else x)
    df.dropna(axis=0, inplace=True)
    return df, day


async def get_standard_timetable_for_user_6_9(class_, day):
    if not os.path.exists(path_to_timetables_csv + f'{class_}.csv'):
        return pd.DataFrame(), -1
    timetable_, day = await extract_timetable_for_day_6_9(day, class_)
    return timetable_, day


async def get_timetable_for_user_6_9(context, class_):
    if not os.path.exists(path_to_timetables_csv + f'{class_}.csv'):
        return pd.DataFrame(), -1
    # day = (datetime.now() - timedelta(hours=3)).weekday()
    # !!!!!!!!!!!!!!!!!!!
    now_ = datetime.now()  # - timedelta(hours=3)
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_timetable_for_day_6_9(0, class_)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_timetable_for_day_6_9(day, class_)
    last_les_end_h, last_les_end_m = map(int,
                                         timetable_.index.values[-1].split(' - ')[-1]
                                         .split(':'))
    # !!!!!!!!!!!!!!!!!!!!!
    h, m = now_.hour, now_.minute
    if (h, m) > (last_les_end_h, last_les_end_m):
        context.user_data['NEXT_DAY_TT'] = True
        if day == 5:
            timetable_, day = await extract_timetable_for_day_6_9(0, class_)
            return timetable_, 0
        timetable_, day = await extract_timetable_for_day_6_9(day + 1, class_)
        # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
    else:
        context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


async def extract_timetable_for_day(day, full_name, class_):
    df = pd.read_csv(path_to_timetables_csv + f'{full_name} {class_}.csv')
    df = df.iloc[day].to_frame()
    df = df[df[day] != '--'][day]
    return df, day


async def get_standard_timetable_for_user(full_name, class_, day):
    if not os.path.exists(path_to_timetables_csv + f'{full_name} {class_}.csv'):
        return pd.DataFrame(), -1
    timetable_, day = await extract_timetable_for_day(day, full_name, class_)
    return timetable_, day


async def get_timetable_for_user(context, full_name, class_):
    if not os.path.exists(path_to_timetables_csv + f'{full_name} {class_}.csv'):
        return pd.DataFrame(), -1
    now_ = datetime.now()  # - timedelta(hours=3)
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_timetable_for_day(0, full_name, class_)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_timetable_for_day(day, full_name, class_)
    last_les_end_h, last_les_end_m = map(int,
                                         timetable_.index.values[-1].split(' - ')[-1]
                                         .split(':'))
    h, m = now_.hour, now_.minute
    if (h, m) > (last_les_end_h, last_les_end_m):
        context.user_data['NEXT_DAY_TT'] = True
        if day == 5:
            timetable_, day = await extract_timetable_for_day(0, full_name, class_)
            return timetable_, 0
        timetable_, day = await extract_timetable_for_day(day + 1, full_name, class_)
        # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
    else:
        context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


async def get_edits_in_timetable(next_day_tt):
    # filename format: DD.MM.YYYY
    time_ = datetime.now()
    if next_day_tt and time_.weekday() == 5:
        time_ = time_ + timedelta(days=1)
        next_day_tt = '2DAYS'
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

    if not next_day_tt:
        day = "*Изменения на сегодня*"
        path_ = path_to_changes + today_file
    else:
        if next_day_tt == '2DAYS':
            day = "*Изменения на послезавтра*"
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
                                    'Урок по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет\nпо расписанию': 'Урок по расписанию'})
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


def update_db(update, name, surname, grade):
    user__id = update.message.from_user.id
    user = db_sess.query(User).filter(User.telegram_id == user__id).first()
    user.surname = surname
    user.name = name
    user.grade = grade
    user.number = grade[:-1]
    if grade == 'АДМИН':
        user.number = 'АДМИН'
    db_sess.commit()


def extra_lessons_return(id, button_text):
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == id).all()
    full_text = []
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text = "⤵️\n"
            text += f"📚 {extra.title} 📚\n"
            text += f"🕝 {extra.time} 🕝\n"
            if extra.teacher.count(".") > 1:
                text += f'Учитель: {extra.teacher}\n'
            place = ""
            if "зал" in extra.place or "online" in extra.place:
                place = extra.place
            else:
                place = f"{extra.place} кабинет"
            text += f'🏫 Место проведения: {place} 🏫\n'
            full_text.append(text)
    return "".join(full_text)
