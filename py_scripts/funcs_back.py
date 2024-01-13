# -*- coding: utf-8 -*-
import functools

import pandas as pd
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, Bot
from sqlalchemy_scripts import db_session
from sqlalchemy_scripts.users import User
from datetime import datetime, timedelta
import string
from py_scripts.config import BOT_TOKEN
import os
from py_scripts.consts import path_to_changes
import pdfplumber


db_session.global_init("database/telegram_bot.db")
bot = Bot(BOT_TOKEN)
db_sess = db_session.create_session()


async def check_busy(update, context, flag=False):
    if context.user_data.get('in_conversation'):
        cmd = context.user_data.get("DIALOG_CMD")
        if cmd and not flag:
            await update.message.reply_text(f'Сначала нужно завершить предыдущую цепочку команд: {cmd}')
        return True
    return False


def throttle():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            now_ = datetime.now()
            last_time = args[2].user_data.get('last_time')
            if not last_time:
                args[2].user_data['last_time'] = now_
                return await func(*args, **kwargs)
            elif last_time + timedelta(seconds=0.5) <= now_:
                args[2].user_data['last_time'] = now_
                return await func(*args, **kwargs)
            else:
                return await trottle_ans(*args, **kwargs)
        return wrapped
    return wrapper


def throttle2():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            now_ = datetime.now()
            last_time = args[2].user_data.get('last_time2')
            if not last_time:
                args[2].user_data['last_time2'] = now_
                return await func(*args, **kwargs)
            elif last_time + timedelta(seconds=0.5) <= now_:
                args[2].user_data['last_time2'] = now_
                return await func(*args, **kwargs)
        return wrapped
    return wrapper


async def trottle_ans(*args, **kwargs):
    await args[1].message.reply_text('🧨 Пожалуйста, пишите помедленнее!')


async def timetable_kbrd():
    btn = KeyboardButton('📚Ближайшее расписание📚')
    btn3 = KeyboardButton('🎨Мои кружки🎨')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    inten = KeyboardButton('⚡️Интенсивы⚡️')
    kbd = ReplyKeyboardMarkup([[btn], arr, [inten], [btn3]], resize_keyboard=True)
    return kbd


async def extra_school_timetable_kbrd():
    btn = KeyboardButton('♟️Сегодня♟️')
    btn2 = KeyboardButton('🎭Все кружки🎭')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn, btn2], arr], resize_keyboard=True)
    return kbd


async def intensive_kbrd():
    with open('intensives.txt', mode='r', encoding='utf-8') as f:
        subjects = list(set(f.read().split('\n')[:-1]))
    f.close()
    kbd = ReplyKeyboardMarkup([[i] for i in subjects], resize_keyboard=True)
    return kbd


def prepare_for_markdown(text):
    res = ''
    for i in text:
        if i in string.punctuation:
            res += '\\' + i
        else:
            res += i
    return res


def put_to_db(update, name, surname, role, username, grade=None):
    user__id = update.message.from_user.id
    chat_id = update.message.chat.id
    num = grade
    if role != 'admin' and role != 'teacher':
        num = num[:-1]
    if not db_sess.query(User).filter(User.chat_id == chat_id).first():
        user = User(telegram_id=user__id, chat_id=chat_id, surname=surname, name=name, role=role,
                    grade=grade, number=num, telegram_tag=username)
        db_sess.add(user)
        db_sess.commit()


def update_db(update, name, surname, role, username, grade=None):
    chat_id = update.message.chat.id
    user = db_sess.query(User).filter(User.chat_id == chat_id).first()
    user.surname = surname
    user.name = name
    user.role = role
    user.grade = grade
    user.telegram_tag = username
    if role != 'admin' and role != 'teacher':
        user.number = grade[:-1]
    else:
        user.number = grade
    db_sess.commit()


async def save_edits_in_timetable_csv(date):
    # filename format: DD.MM.YYYY
    path_ = path_to_changes + date + '.pdf'
    dfs = []
    fl_first_time = True
    with pdfplumber.open(path_) as pdf:
        tables = []
        t = []
        for page in pdf.pages:
            t2 = page.extract_tables()
            t.extend(t2[0])
        arr = []
        t2 = []
        intensive_subjects_arr = {}
        intensive_title = []
        first_time_intensive_title = True
        intensive_subject_name = ''
        intensive_handler = None
        flag_started_lesson = False
        days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
        for j in range(len(t)):
            cnt = 0
            flag = False
            for el in t[j]:
                if not el:
                    cnt += 1
                if el and ('Изменения' in el or any([ddd in el for ddd in days])):
                    flag = True
                if el and 'интенсив' in el.lower():
                    intensive_handler = j  # запоминаем индекс начала интенсивов
            if cnt == 5 and arr and all(
                    [isinstance(Q, str) and not Q for Q in t[j]]):
                t2.append(arr)
                arr = []
                continue
            elif flag or intensive_handler and j - intensive_handler == 0:
                if arr:
                    t2.append(arr)
                    arr = []
                    continue
            elif intensive_handler:
                new_arr = []
                for elem in t[j]:
                    if elem:
                        elem = elem.strip(' ').strip('\n').strip(' ').strip('\n')
                        new_arr.append(elem)
                if len(new_arr) == 1:
                    intensive_subject_name = new_arr[0]
                    intensive_subjects_arr[intensive_subject_name] = [intensive_title.copy()]
                    continue
                if len(new_arr) == 2:
                    new_arr = [intensive_subjects_arr[intensive_subject_name][-1][0]] + new_arr
                if first_time_intensive_title:
                    intensive_title = new_arr.copy()
                    intensive_title[-1] = 'Инфо'
                    first_time_intensive_title = False
                else:
                    intensive_subjects_arr[intensive_subject_name].append(new_arr)
            else:
                if t[j][1] and not flag_started_lesson or 'Предмет' == t[j][3]:
                    tmp = t[j]
                    while len(tmp) != 5:
                        tmp.append(None)
                        if len(tmp) > 5:
                            raise Exception("Неверный формат таблицы")
                    if tmp[3] and 'Замен' in tmp[3] and tmp[4] is not None:
                        tmp[3] += tmp[4]
                        tmp[4] = None
                    for i in range(len(tmp)):
                        if tmp[i]:
                            tmp[i] = tmp[i].strip(' ').strip('\n').strip(' ').strip('\n')
                    arr.append(tmp)
                elif t[j][0] and all([isinstance(Q, str) and not Q for Q in t[j][1:]]):
                    tmp = t[j]
                    for i in range(len(tmp)):
                        if tmp[i]:
                            tmp[i] = tmp[i].strip(' ').strip('\n').strip(' ').strip('\n')
                    arr.append(tmp)
                    flag_started_lesson = True
                else:
                    for el in range(len(t[j])):
                        if t[j][el]:
                            try:
                                arr[-1][el] += '\n' + t[j][el]
                                arr[-1][el] = arr[-1][el].strip(' ').strip('\n').strip(' ').strip('\n')
                            except Exception:
                                print(j, el)
                    flag_started_lesson = False
        if arr:
            t2.append(arr)
        if t2:
            if len(t2) == 1:
                tables.append(t2[0])
            else:
                tables.extend(t2)
        elif len(t) == 1:
            tables.append(t[0])
        elif len(t) > 1:
            tables.extend(t)
        for table in tables:
            df = pd.DataFrame(table[1:], columns=table[0])
            df.dropna(how='all', axis=1, inplace=True)
            df = df.fillna('')
            df = df.rename(columns={None: 'Замена2', 'Замена': 'Замены',
                                    'Замена кабинета': 'Замены кабинетов',
                                    "№\nурока": "Урок №",
                                    "№ урока": "Урок №",
                                    "№урока": "Урок №",
                                    "№": "Урок №",
                                    'Замена\nкабинета': 'Замены кабинетов',
                                    'Заменакабинета': 'Замены кабинетов',
                                    'Урок по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет\nпо расписанию': 'Урок по расписанию',
                                    'None': 'Замена2'})
            cols_vals = df.columns.values
            if fl_first_time:
                if 'Замена2' in cols_vals:
                    df['Замены'] = df['Замены'] + '//' + df['Замена2']
                    df.drop('Замена2', axis=1, inplace=True)
                elif 'Замены' in cols_vals:
                    df['Замены'] = df['Замены'] + '//'
                fl_first_time = False
            if "Замены кабинетов" in cols_vals:
                if 'Замена2' in cols_vals:
                    df['Замены кабинетов'] = df['Замены кабинетов'] + df['Замена2']
                    df = df.rename(columns={'Замена2': None})
                    df[None] = ''
                    df.drop(labels=[None], axis=1, inplace=True)
                for k in range(len(table)):
                    if table[k].count(None) == 2:
                        table[k] = [table[k][0], '', '', table[k][1]]
            indexes = df.index.values
            if 'Замены' in df.columns.values:
                curr_ind = indexes[-1] + 1
                for line in indexes:
                    if line == 0:
                        continue
                    classes = df.loc[line]['Класс'].split('\n')
                    urok_num = df.loc[line]['Урок №'].split('\n')
                    urok_po_rasp = df.loc[line]['Урок по расписанию'].split('\n')
                    zameny = df.loc[line]['Замены'].split('\n')
                    summ = 0
                    for i in ['6', '7', '8', '9', '10', '11']:
                        for cl in classes:
                            summ += cl.count(i)
                    if summ > 1:
                        urok_num = urok_num * summ
                        zameny = zameny * summ
                        df.at[line, 'Класс'] = classes[0]
                        df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                        df.at[line, 'Урок №'] = urok_num[0]
                        df.at[line, 'Замены'] = zameny[0]
                        for i in range(1, summ):
                            df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                            curr_ind += 1
                    elif len(urok_num) != 1:
                        classes = classes * len(urok_num)
                        zameny_ = "\n".join(zameny)
                        lesson, teacher_ = zameny_.split('//')
                        lesson = lesson.split('\n')
                        teacher_ = teacher_.split('\n')
                        teacher = []
                        zameny = []
                        for i in range(0, len(teacher_), 2):
                            teacher.append(f"{teacher_[i]}\n{teacher_[i + 1]}")
                        for i in range(len(urok_num)):
                            zameny.append(f"{lesson[i]}//{teacher[i]}")
                        df.at[line, 'Класс'] = classes[0]
                        df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                        df.at[line, 'Урок №'] = urok_num[0]
                        df.at[line, 'Замены'] = zameny[0]
                        for i in range(1, len(urok_num)):
                            df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                            curr_ind += 1
            dfs.append(df)
    pdf.close()
    try:
        os.remove(path_to_changes + f'{date}_lessons.csv')
    except Exception:
        pass
    try:
        os.remove(path_to_changes + f'{date}_cabinets.csv')
    except Exception:
        pass
    if not os.path.exists('intensives.txt'):
        with open('intensives.txt', mode='w', encoding='utf-8') as f:
            f.write('')
        f.close()
    with open('intensives.txt', mode='a', encoding='utf-8') as f:
        for key, value in intensive_subjects_arr.items():
            df = pd.DataFrame(value[1:], columns=value[0])
            df.to_csv(path_to_changes + f'intensive_{key}_{date}.csv')
            f.write(f'{key}\n')
    f.close()
    for i in range(len(dfs)):
        dfs[i] = dfs[i].sort_values(['Урок №'])
        name = 'cabinets'
        if 'Замены' in dfs[i].columns.values:
            name = 'lessons'
        dfs[i].to_csv(path_to_changes + f'{date}_{name}.csv')


async def get_intensive(subject, teacher=False, parallel=10, surname='Бибиков', name='Павел'):
    time_ = datetime.now()
    day_ = str(time_.day).rjust(2, '0')
    month_ = str(time_.month).rjust(2, '0')
    today_file = f'changes_tt/intensive_{subject}_{day_}.{month_}.{time_.year}.csv'
    time_copy = f'{day_}.{month_}.{time_.year}'
    if time_.weekday() == 5:
        time_ = time_ + timedelta(days=1)
    time_2 = time_ + timedelta(days=1)
    day_ = str(time_2.day).rjust(2, '0')
    month_ = str(time_2.month).rjust(2, '0')
    tomorrow_file = f'changes_tt/intensive_{subject}_{day_}.{month_}.{time_2.year}.csv'
    if not (os.path.exists(today_file) or os.path.exists(tomorrow_file)):
        return f'В ближайшее время у Вас нет интенсивов по предмету {prepare_for_markdown(subject)}\.'
    today_text = ''
    tomorrow_text = ''
    if os.path.exists(today_file):
        df = pd.read_csv(today_file, dtype=object)
        df['Инфо'] = df['Инфо'].str.split('\n').str.join(', ')
        for i in range(len(df.index)):
            if teacher:
                if f'{surname} {name[0]}' in df.iloc[i]['Инфо']:
                    today_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}'))
            else:
                if f'{parallel}' in df.iloc[i]['Класс']:
                    today_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}'))
        if today_text:
            today_text = (f'Интенсивы на *{prepare_for_markdown(time_copy)}* по предмету '
                          f'*{prepare_for_markdown(subject)}*\n\n') + today_text + '\n\n'
    if os.path.exists(tomorrow_file):
        df = pd.read_csv(tomorrow_file, dtype=object)
        df['Инфо'] = df['Инфо'].str.split('\n').str.join(', ')
        for i in range(len(df.index)):
            if teacher:
                if f'{surname} {name[0]}' in df.iloc[i]['Инфо']:
                    tomorrow_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}\n'))
            else:
                if f'{parallel}' in df.iloc[i]['Класс']:
                    tomorrow_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}\n'))
        if tomorrow_text:
            tomorrow_text = (f'Интенсивы на *{prepare_for_markdown(f"{day_}.{month_}.{time_2.year}")}* по предмету '
                          f'*{prepare_for_markdown(subject)}*\n\n') + tomorrow_text + '\n\n'
    res = today_text + tomorrow_text
    if not res:
        return f'В ближайшее время у Вас нет интенсивов по предмету {prepare_for_markdown(subject)}\.'
    return res


async def get_edits_in_timetable(next_day_tt):
    # filename format: DD.MM.YYYY
    time_ = datetime.now()
    if next_day_tt and time_.weekday() == 5:
        time_ = time_ + timedelta(days=1)
        next_day_tt = '2DAYS'
    day_ = str(time_.day).rjust(2, '0')
    month_ = str(time_.month).rjust(2, '0')
    today_file1 = f'{day_}.{month_}.{time_.year}_lessons.csv'
    today_file2 = f'{day_}.{month_}.{time_.year}_cabinets.csv'
    time_2 = time_ + timedelta(days=1)
    day_ = str(time_2.day).rjust(2, '0')
    month_ = str(time_2.month).rjust(2, '0')
    tomorrow_file1 = f'{day_}.{month_}.{time_2.year}_lessons.csv'
    tomorrow_file2 = f'{day_}.{month_}.{time_2.year}_cabinets.csv'

    if next_day_tt:
        if not (os.path.exists(path_to_changes + tomorrow_file1) or
                os.path.exists(path_to_changes + tomorrow_file2)):
            # Файла с изменениями нет
            return [], ''
    else:
        if not (os.path.exists(path_to_changes + today_file1) or
                os.path.exists(path_to_changes + today_file2)):
            # Файла с изменениями нет
            return [], ''

    if not next_day_tt:
        day = "*Изменения на сегодня*"
        path_1 = path_to_changes + today_file1
        path_2 = path_to_changes + today_file2
    else:
        if next_day_tt == '2DAYS':
            day = "*Изменения на послезавтра*"
        else:
            day = "*Изменения на завтра*"
        path_1 = path_to_changes + tomorrow_file1
        path_2 = path_to_changes + tomorrow_file2
    day = prepare_for_markdown('🔔') + day + prepare_for_markdown('🔔\n')
    dfs = []
    if os.path.exists(path_1):
        df = pd.read_csv(path_1, dtype=object)
        df.fillna('', inplace=True)
        dfs.append(df)
    if os.path.exists(path_2):
        df = pd.read_csv(path_2, dtype=object)
        df.fillna('', inplace=True)
        dfs.append(df)
    return dfs, day
