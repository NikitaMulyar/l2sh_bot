# -*- coding: utf-8 -*-
import functools

import pandas as pd
import telegram
from telegram import KeyboardButton, ReplyKeyboardMarkup, Bot, Update
from telegram.ext import ContextTypes
from sqlalchemy_scripts import db_session
from sqlalchemy_scripts.users import User
from datetime import datetime, timedelta
import string
import os
from py_scripts.consts import path_to_changes
import pdfplumber


async def check_busy(update: Update, context: ContextTypes.DEFAULT_TYPE, flag=False):
    if context.user_data.get('in_conversation'):
        cmd = context.user_data.get("DIALOG_CMD")
        if cmd and not flag:
            await update.message.reply_text(f'⚠️ *Сначала нужно завершить предыдущую цепочку команд\: {prepare_for_markdown(cmd)}*',
                                            parse_mode='MarkdownV2')
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
    #inten = KeyboardButton('⚡️Интенсивы⚡️')
    kbd = ReplyKeyboardMarkup([[btn], arr, [btn3]], resize_keyboard=True)
    return kbd


async def extra_school_timetable_kbrd():
    btn = KeyboardButton('♟️Сегодня♟️')
    btn2 = KeyboardButton('🎭Все кружки🎭')
    arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    kbd = ReplyKeyboardMarkup([[btn, btn2], arr], resize_keyboard=True)
    return kbd


async def intensive_kbrd():
    with open('intensives.txt', mode='r', encoding='utf-8') as f:
        subjects = set((f.read()).split('\n')[:-1])
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


def put_to_db(update: Update, name, surname, role, username, grade=None):
    db_sess = db_session.create_session()
    user__id = update.message.from_user.id
    chat_id = update.message.chat_id
    num = grade
    if role != 'admin' and role != 'teacher':
        num = num[:-1]
    if not db_sess.query(User).filter(User.chat_id == chat_id).first():
        user = User(telegram_id=user__id, chat_id=chat_id, surname=surname, name=name, role=role,
                    grade=grade, number=num, telegram_tag=username)
        db_sess.add(user)
        db_sess.commit()
    db_sess.close()


def update_db(update: Update, name, surname, role, username, grade=None):
    db_sess = db_session.create_session()
    chat_id = update.message.chat_id
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
    db_sess.close()


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
                if el and ('изменения' in el.lower() or any([ddd in el for ddd in days])):
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
                if len(new_arr) == 1 and 'кл' not in new_arr[0].lower():
                    intensive_subject_name = new_arr[0]
                    intensive_subjects_arr[intensive_subject_name] = [intensive_title.copy()]
                    continue
                if len(new_arr) == 2:
                    flag_missed_class = True
                    flag_missed_lesson = True
                    flag_missed_subject = True
                    for i in new_arr:
                        if 'кл' in i.lower():
                            flag_missed_class = False
                        if i.count(':') != 0:
                            flag_missed_lesson = False
                        if i.count('.') >= 2:
                            flag_missed_subject = False
                    if flag_missed_class:
                        new_arr = [intensive_subjects_arr[intensive_subject_name][-1][0]] + new_arr
                    if flag_missed_lesson:
                        new_arr = [new_arr[0], intensive_subjects_arr[intensive_subject_name][-1][1], new_arr[1]]
                    if flag_missed_subject:
                        new_arr = new_arr + [intensive_subjects_arr[intensive_subject_name][-1][2]]
                if len(new_arr) == 1:
                    flag_have_class = False
                    flag_have_lesson = False
                    flag_have_subject = False
                    for i in new_arr:
                        if 'кл' in i.lower():
                            flag_have_class = True
                        if i.count(':') != 0:
                            flag_have_lesson = True
                        if i.count('.') >= 2:
                            flag_have_subject = True
                    if flag_have_class:
                        new_arr.extend(intensive_subjects_arr[intensive_subject_name][-1][1:])
                    if flag_have_lesson:
                        new_arr = [intensive_subjects_arr[intensive_subject_name][-1][0],
                                   new_arr[0],
                                   intensive_subjects_arr[intensive_subject_name][-1][2]]
                    if flag_have_subject:
                        new_arr = intensive_subjects_arr[intensive_subject_name][-1][:2] + [
                            new_arr[0]]
                if first_time_intensive_title and len(new_arr) == 3:
                    intensive_title = new_arr.copy()
                    intensive_title[-1] = 'Инфо'
                    first_time_intensive_title = False
                elif len(new_arr) == 3:
                    intensive_subjects_arr[intensive_subject_name].append(new_arr)
                if len(new_arr) == 4:
                    subjects = ['физика', ' матем', 'эколог', 'эконом']
                    ind_subj = None
                    for i in range(len(new_arr)):
                        for possib_subj in subjects:
                            if possib_subj in new_arr[i].lower():
                                ind_subj = i
                                break
                        if ind_subj:
                            break
                    title = ['Класс', 'Время', 'Инфо']
                    if not intensive_subjects_arr.get(new_arr[ind_subj]):
                        intensive_subjects_arr[new_arr[ind_subj]] = [title]
                    intensive_subjects_arr[new_arr[ind_subj]].append(new_arr[:ind_subj] + new_arr[ind_subj + 1:])
            else:
                if t[j][1] and not flag_started_lesson or 'Предмет' == t[j][3]:
                    tmp = t[j]
                    while len(tmp) != 5:
                        tmp.append(None)
                        if len(tmp) > 5:
                            raise Exception("Неверный формат таблицы")
                    if tmp[3] and 'замен' in tmp[3].lower() and tmp[4] is not None:
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
            df.columns = [el.capitalize() if el else el for el in df.columns.values]
            df = df.rename(columns={None: 'Замена2', 'Замена': 'Замены',
                                    'Замена кабинета': 'Замены кабинетов',
                                    "№\nурока": "Урок №",
                                    "№ урока": "Урок №",
                                    "№урока": "Урок №",
                                    "№": "Урок №",
                                    "Урок": "Урок №",
                                    'Замена\nкабинета': 'Замены кабинетов',
                                    'Кабинет': 'Замены кабинетов',
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
    parallel = int(parallel)
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
        return f'*В ближайшее время у Вас нет интенсивов по предмету {prepare_for_markdown(subject)}\.*'
    today_text = ''
    tomorrow_text = ''
    if os.path.exists(today_file):
        df = pd.read_csv(today_file, dtype=object)
        df['Инфо'] = df['Инфо'].str.split('\n').str.join(', ')
        for i in range(len(df.index)):
            if teacher:
                if f'{surname} {name[0]}' in df.iloc[i]['Инфо']:
                    today_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}\n'))
            else:
                if f'{parallel}' in df.iloc[i]['Класс'] or ('-' in df.iloc[i]['Класс'] and
                                                            (f'{parallel - 1}' in df.iloc[i]['Класс'] or
                                                             f'{parallel + 1}' in df.iloc[i]['Класс'])):
                    today_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}\n'))
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
                if f'{parallel}' in df.iloc[i]['Класс'] or ('-' in df.iloc[i]['Класс'] and
                                                            (f'{parallel - 1}' in df.iloc[i][
                                                                'Класс'] or
                                                             f'{parallel + 1}' in df.iloc[i][
                                                                 'Класс'])):
                    tomorrow_text += ('*' + prepare_for_markdown(f'{df.iloc[i]["Время"]}') + '*' +
                                   prepare_for_markdown(f' - {df.iloc[i]["Класс"]}: {df.iloc[i]["Инфо"]}\n'))
        if tomorrow_text:
            tomorrow_text = (f'Интенсивы на *{prepare_for_markdown(f"{day_}.{month_}.{time_2.year}")}* по предмету '
                          f'*{prepare_for_markdown(subject)}*\n\n') + tomorrow_text + '\n\n'
    res = today_text + tomorrow_text
    if not res:
        return f'*В ближайшее время у Вас нет интенсивов по предмету {prepare_for_markdown(subject)}\.*'
    return res


async def get_edits_in_timetable(date):
    # filename format: DD.MM.YYYY
    file1 = f'{date}_lessons.csv'
    file2 = f'{date}_cabinets.csv'

    if not (os.path.exists(path_to_changes + file1) or
            os.path.exists(path_to_changes + file2)):
        # Файла с изменениями нет
        return [], ''

    day = f"*Изменения на {prepare_for_markdown(date)}*"
    path_1 = path_to_changes + file1
    path_2 = path_to_changes + file2

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
