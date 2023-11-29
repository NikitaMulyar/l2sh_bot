# -*- coding: utf-8 -*-
import pandas as pd
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


def throttle2(func):
    def wrapper(*args, **kwargs):
        now_ = datetime.now()
        last_time = args[2].user_data.get('last_time2')
        if not last_time:
            args[2].user_data['last_time2'] = now_
            asyncio.gather(func(*args, **kwargs))
        elif last_time + timedelta(seconds=0.5) <= now_:
            args[2].user_data['last_time2'] = now_
            asyncio.gather(func(*args, **kwargs))
    return wrapper


async def trottle_ans(*args, **kwargs):
    await args[1].message.reply_text('🧨 Пожалуйста, пишите помедленнее!')


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
                await asyncio.gather(bot.send_message(user.chat_id, text, parse_mode='MarkdownV2'))
            else:
                await asyncio.gather(bot.send_message(user.chat_id, text))
        except telegram.error.TelegramError:
            pass


async def write_admins(bot: telegram.Bot, text, parse_mode=None):
    all_users = db_sess.query(User).filter(User.grade == "АДМИН").all()
    for user in all_users:
        try:
            if parse_mode:
                await asyncio.gather(bot.send_message(user.chat_id, text, parse_mode='MarkdownV2'))
            else:
                await asyncio.gather(bot.send_message(user.chat_id, text))
        except telegram.error.TelegramError:
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


async def save_edits_in_timetable_csv(date):
    # filename format: DD.MM.YYYY
    path_ = path_to_changes + date + '.pdf'
    dfs = []
    cabs = ['Урок №', 'Класс', 'Урок по расписанию', 'Замены кабинетов']
    lessons = ['Урок №', 'Класс', 'Урок по расписанию', 'Замены']
    cabs2 = ['Класс', 'Урок №', 'Урок по расписанию', 'Замены кабинетов']
    lessons2 = ['Класс', 'Урок №', 'Урок по расписанию', 'Замены']
    fl_first_time = True
    are_working_with_cabs = False
    with pdfplumber.open(path_) as pdf:
        try:
            tables = []
            t = []
            for page in pdf.pages:
                t2 = page.extract_tables()
                t.extend(t2[0])
            arr = []
            t2 = []
            flag_started_lesson = False
            flag_was_space_str = False
            days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
            for j in range(len(t)):
                cnt = 0
                flag = False
                for el in t[j]:
                    if not el:
                        cnt += 1
                    if el and ('Изменения' in el or any([ddd in el for ddd in days])):
                        flag = True
                    if isinstance(el, str) and not el:
                        flag_was_space_str = True
                if cnt == 5 and arr and all(
                        [isinstance(Q, str) and not Q for Q in t[j]]):
                    t2.append(arr)
                    arr = []
                    continue
                elif flag:
                    continue
                else:
                    if t[j][1] and not flag_started_lesson or t[j][3] and 'Предмет' == t[j][3]:
                        tmp = t[j]
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
            if not flag_was_space_str:
                raise Exception
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
        except Exception as e:
            print(e)
            tables = []
            for page in pdf.pages:
                t = page.extract_tables()
                if len(t) == 1:
                    tables.append(t[0])
                elif len(t) > 1:
                    tables.extend(t)
        for table in tables:
            if len(table[0]) < 3:
                continue
                # какие-то беды с парсингом
            df = pd.DataFrame(table[1:], columns=table[0])
            df.dropna(how='all', axis=1, inplace=True)
            df = df.fillna('')
            df = df.rename(columns={None: 'Замена2', 'Замена': 'Замены',
                                    'Замена кабинета': 'Замены кабинетов',
                                    "№\nурока": "Урок №",
                                    "№ урока": "Урок №",
                                    'Замена\nкабинета': 'Замены кабинетов',
                                    'Урок по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет\nпо расписанию': 'Урок по расписанию'})
            if fl_first_time:
                cols_vals = df.columns.values
                if 'Замена2' in cols_vals:
                    df['Замены'] = df['Замены'] + '//' + df['Замена2']
                    df.drop('Замена2', axis=1, inplace=True)
                elif 'Замены' in cols_vals:
                    df['Замены'] = df['Замены'] + '//'
                fl_first_time = False
            if "Замены кабинетов" in df.columns.values:
                are_working_with_cabs = True
                for k in range(len(table)):
                    if table[k].count(None) == 2:
                        table[k] = [table[k][0], '', '', table[k][1]]
            fl_cabs = False
            fl_lessons = False
            for i in range(len(cabs)):
                if cabs[i] != df.columns.values[i] and df.columns.values[i] != cabs2[i]:
                    fl_cabs = True
                    break
            for i in range(len(lessons)):
                if lessons[i] != df.columns.values[i] and df.columns.values[i] != lessons2[i]:
                    fl_lessons = True
                    break
            if fl_lessons and fl_cabs and not are_working_with_cabs:
                for k in range(len(table)):
                    if len(table[k]) == 5:
                        table[k] = table[k][:3] + ["//".join(table[k][3:])]
                    else:
                        table[k] = table[k][:3] + [table[k][3] + "//"]
                df = pd.DataFrame(table, columns=list(dfs[-1].columns.values))
                df = df.fillna('')
                last = dfs[-1].index.values[-1]
                for ind in df.index.values:
                    df = df.rename(index={ind: last + ind + 1})
                # Далее: если формат такой, какой был 19.10.2023
                indexes = df.index.values
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
                dfs[-1] = pd.concat([dfs[-1], df], axis='rows')
            elif fl_lessons and fl_cabs and are_working_with_cabs:
                df = pd.DataFrame(table, columns=list(dfs[-1].columns.values))
                df = df.fillna('')
                last = dfs[-1].index.values[-1]
                for ind in df.index.values:
                    df = df.rename(index={ind: last + ind + 1})
                dfs[-1] = pd.concat([dfs[-1], df], axis='rows')
            else:
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
    try:
        os.remove(path_to_changes + f'{date}_lessons.csv')
    except Exception:
        pass
    try:
        os.remove(path_to_changes + f'{date}_cabinets.csv')
    except Exception:
        pass
    for i in range(len(dfs)):
        dfs[i] = dfs[i].sort_values(['Урок №'])
        name = 'cabinets'
        if 'Замены' in dfs[i].columns.values:
            name = 'lessons'
        dfs[i].to_csv(path_to_changes + f'{date}_{name}.csv')


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
