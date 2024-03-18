from py_scripts.funcs_back import prepare_for_markdown, get_edits_in_timetable
from py_scripts.consts import days_from_short_text_to_num, days_from_num_to_full_text_formatted, lessons_keys
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
from py_scripts.consts import path_to_timetables_csv, for_datetime
from sqlalchemy_scripts.user_to_extra import Extra, Extra_to_User
from telegram.ext import ContextTypes
from telegram import Update
import re
from sqlalchemy_scripts import db_session


async def extract_timetable_for_day_6_9(day, class_):
    df = pd.read_csv(path_to_timetables_csv + f'{class_}.csv')
    df = df.iloc[day].to_frame()
    df[day] = df[day].str.strip('###')
    df[day] = df[day].apply(lambda x: np.NaN if x == '' else x)
    df.dropna(axis=0, inplace=True)
    return df[day], day


async def get_standard_timetable_for_user_6_9(class_, day):
    if not os.path.exists(path_to_timetables_csv + f'{class_}.csv'):
        return pd.DataFrame(), -1

    timetable_, day = await extract_timetable_for_day_6_9(day, class_)
    return timetable_, day


async def get_timetable_for_user_6_9(context: ContextTypes.DEFAULT_TYPE, class_):
    if not os.path.exists(path_to_timetables_csv + f'{class_}.csv'):
        return pd.DataFrame(), -1

    now_ = datetime.now()
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_timetable_for_day_6_9(0, class_)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_timetable_for_day_6_9(day, class_)
    context.user_data['NEXT_DAY_TT'] = False

    last_les_end_h, last_les_end_m = map(int,
                                         timetable_.index.values[-1].split(' - ')[-1]
                                         .split(':'))
    h, m = now_.hour, now_.minute
    if (h, m) > (last_les_end_h, last_les_end_m):
        context.user_data['NEXT_DAY_TT'] = True
        if day == 5:
            timetable_, day = await extract_timetable_for_day_6_9(0, class_)
            return timetable_, 0
        timetable_, day = await extract_timetable_for_day_6_9(day + 1, class_)
    return timetable_, day


async def extract_timetable_for_day(day, full_name, class_):
    df = pd.read_csv(path_to_timetables_csv + f'{full_name} {class_}.csv')
    df.drop(['Unnamed: 0'], axis=1, inplace=True)
    df = df.iloc[day].to_frame()
    df.dropna(axis=0, inplace=True)
    return df[day], day


async def get_standard_timetable_for_user(full_name, class_, day):
    if not os.path.exists(path_to_timetables_csv + f'{full_name} {class_}.csv'):
        return pd.DataFrame(), -1

    timetable_, day = await extract_timetable_for_day(day, full_name, class_)
    return timetable_, day


async def get_timetable_for_user(context: ContextTypes.DEFAULT_TYPE, full_name, class_):
    if not os.path.exists(path_to_timetables_csv + f'{full_name} {class_}.csv'):
        return pd.DataFrame(), -1

    now_ = datetime.now()
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_timetable_for_day(0, full_name, class_)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_timetable_for_day(day, full_name, class_)
    context.user_data['NEXT_DAY_TT'] = False

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
    return timetable_, day


async def create_list_of_edits_lessons_for_student(df: pd.DataFrame, student_class):
    res = []
    for j in df.index.values:
        number_of_lesson = " ".join(df.iloc[j]['Урок №'].split('\n'))
        if not " ".join(df.iloc[j]['Класс'].split('\n')):
            continue

        pattern = '[16789]+[01]*[а-дА-Д]*'
        r_ = re.findall(pattern, " ".join(df.iloc[j]['Класс'].split('\n')))
        flag = False
        for el in r_:
            el = el.upper()
            if student_class[:-1] in el and student_class[-1] in el:
                flag = True
                break
            if el.isdigit() and student_class[:-1] in el:
                flag = True
                break
        if not flag:
            continue

        if 'Замены' in df.columns.values:
            if df.iloc[j]['Урок №'] == '' and j == 0:
                continue
            subject, teacher_cabinet = df.iloc[j]['Замены'].split('//')
            subject = " ".join(subject.split('\n'))
            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
            if teacher_cabinet != '':
                teacher_cabinet = teacher_cabinet.split('\n')
                cabinet = teacher_cabinet[-1]
                teacher = " ".join(teacher_cabinet[:-1])
                if cabinet.count('.') == 2:
                    # Учитель
                    res.append([f"{class__}, ", number_of_lesson, subject,
                                f'{cabinet} каб.', f"{df.iloc[j]['Урок по расписанию']} каб."])  # Кабинет не указан, длина 5
                else:
                    res.append([f"{class__}, ", number_of_lesson,
                                f'{subject}, {cabinet} каб.', teacher,
                                f"{df.iloc[j]['Урок по расписанию']} каб."])  # Все указано, длина 5
            else:
                tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                res.append([f"{class__}, ", number_of_lesson,
                            f"{subject}\n(Урок по расписанию: {tmp} каб.)"])  # Отмена урока, длина 3
        else:
            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
            res.append([f"{class__}, ", number_of_lesson,
                        df.iloc[j]['Замены кабинетов'],
                        f"{df.iloc[j]['Урок по расписанию']} каб."])  # Изменения кабинетов, длина 4
    return sorted(res, key=lambda x: x[1])


async def get_edits_for_student(student_class, date):
    result0 = []
    edits_in_tt, for_which_day = await get_edits_in_timetable(date)
    title_added = False
    if len(edits_in_tt) != 0:
        for df in edits_in_tt:
            sorted_res = await create_list_of_edits_lessons_for_student(df, student_class)
            result = [f'_{prepare_for_markdown(df.columns.values[-1])}_\n']
            flag = False
            for line in sorted_res:
                flag = True
                urok_po_rasp = " ".join(line[-1].split("\n"))
                if len(line) == 3:
                    result.append(prepare_for_markdown(f'{line[0]}{line[1]} урок(и): {line[2]}\n\n'))
                elif len(line) == 4:  # Замены каб.
                    if line[2] == urok_po_rasp == '':
                        result.append(prepare_for_markdown(f'{line[0]}{line[1]}\n\n'))
                    else:
                        result.append(prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                            f'{urok_po_rasp})\n\n'))
                else:
                    result.append(prepare_for_markdown(
                        f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                        f'\n(Урок по расписанию: {urok_po_rasp})\n\n'))
            if flag:
                if not title_added:
                    result0.append(for_which_day)
                    title_added = True
                result0.extend(result)
    return result0


async def get_standard_timetable_with_edits_for_student(day_name, student_class, student_name, student_familia,
                                                        flag=True):
    if int(student_class[:-1]) >= 10:
        lessons, day = await get_standard_timetable_for_user(f'{student_familia} {student_name}',
                                                             student_class, days_from_short_text_to_num[day_name])
    else:
        lessons, day = await get_standard_timetable_for_user_6_9(student_class, days_from_short_text_to_num[day_name])
    txt = prepare_for_markdown((student_familia + ' ' + student_name + ' ' + student_class)
                               .strip(" "))
    if lessons.empty:
        return (f'⚠️ *Ученика \"{txt}\" не найдено или отсутствует расписание для '
                f'{prepare_for_markdown(student_class)} класса*',)
    app = f' для ученика {txt}'
    if not flag:
        app = ''
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*{app}'
    t = ""
    today = datetime.now()
    plus_days = (7 - today.weekday() + day) % 7
    date_future = datetime.now() + timedelta(days=plus_days)
    day_ = str(date_future.day).rjust(2, '0')
    month_ = str(date_future.month).rjust(2, '0')
    date = f'{day_}.{month_}.{date_future.year}'
    edits_text = await get_edits_for_student(student_class, date)
    for txt_info, key in lessons_keys.items():
        if key not in lessons.index.values:
            continue
        pre_lesson_info = lessons.loc[key].split('###')
        t = "".join([t, prepare_for_markdown(txt_info)])
        for lesson_info in pre_lesson_info:
            lesson_info = lesson_info.split('\n')
            lesson_name = lesson_info[-2]
            teachers = "".join(lesson_info[:-2])
            cabinet = lesson_info[-1]
            t = "".join([t, prepare_for_markdown(
                f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')])
        t = f'{t}\n'
    t = f'{t}\n'
    if edits_text:
        t = "\n\n".join([title, f'⚠️ _Обратите внимание\, что у {prepare_for_markdown(student_class)} есть '
                                     f'изменения в расписании\!_', t])
        t = (t, edits_text)
    else:
        t = ("\n\n".join([title, t]),)
    return t


async def get_nearest_timetable_with_edits_for_student(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                                       user):
    if int(user.number) >= 10:
        lessons, day = await get_timetable_for_user(context, f'{user.surname} {user.name}',
                                                    user.grade)
    else:
        lessons, day = await get_timetable_for_user_6_9(context, user.grade)
    if lessons.empty:
        txt = prepare_for_markdown(user.surname + ' ' + user.name + ' ' + user.grade)
        class_txt = user.grade

        await update.message.reply_text(f'⚠️ *Ученика \"{txt}\" не найдено или отсутствует '
                                        f'расписание для {prepare_for_markdown(class_txt)} класса*',
                                        parse_mode='MarkdownV2')
        return
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*'
    t = ""
    time_now = datetime.now()
    plus_days = (7 - time_now.weekday() + day) % 7
    date_future = datetime.now() + timedelta(days=plus_days)
    day_ = str(date_future.day).rjust(2, '0')
    month_ = str(date_future.month).rjust(2, '0')
    date = f'{day_}.{month_}.{date_future.year}'
    for txt_info, key in lessons_keys.items():
        if key not in lessons.index.values:
            continue
        pre_lesson_info = lessons.loc[key].split('###')
        start, end = for_datetime[key]
        if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
            t = "".join([t, '_*', prepare_for_markdown(f'➡️ {txt_info}')])
        else:
            t = "".join([t, prepare_for_markdown(txt_info)])
        for lesson_info in pre_lesson_info:
            lesson_info = lesson_info.split('\n')
            lesson_name = lesson_info[-2]
            teachers = "".join(lesson_info[:-2])
            cabinet = lesson_info[-1]
            t = "".join([t, prepare_for_markdown(
                f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')])
        if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
            t = f'{t}*_'
        t = f'{t}\n'
    t = f'{t}\n'
    edits_text = await get_edits_for_student(user.grade, date)
    if edits_text:
        t = "\n\n".join([title, f'⚠️ _Обратите внимание\, что у Вашего класса есть изменения в расписании\!_',
                              t])
        total_len = len(t)
        ind = 0
        while ind < len(edits_text) and total_len + len(edits_text[ind]) < 4000:
            total_len += len(edits_text[ind])
            ind += 1
        await update.message.reply_text("".join([t, "".join(edits_text[:ind])]), parse_mode='MarkdownV2')
        scnd = "".join(edits_text[ind:])
        if scnd:
            await update.message.reply_text(scnd, parse_mode='MarkdownV2')
    else:
        t = "\n\n".join([title, t])
        await update.message.reply_text(t, parse_mode='MarkdownV2')


def extra_lessons_return(id, button_text):  # Кружки на день для ученика
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    db_sess = db_session.create_session()
    extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == id).all()
    full_text = []
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text = f"⤵️\n📚 {extra.title} 📚\n🕝 {extra.time} 🕝\n"
            if extra.teacher.count(".") > 1:
                text = f'{text}Учитель: {extra.teacher}\n'
            place = f"{extra.place} кабинет"
            if "зал" in extra.place or "online" in extra.place:
                place = extra.place
            text = f'{text}🏫 Место проведения: {place} 🏫\n'
            full_text.append(text)
    db_sess.close()
    return "".join(full_text)
