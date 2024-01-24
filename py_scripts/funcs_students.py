from py_scripts.funcs_back import prepare_for_markdown, get_edits_in_timetable, db_sess
from py_scripts.consts import days_from_short_text_to_num, days_from_num_to_full_text_formatted, lessons_keys
from datetime import datetime
import os
import pandas as pd
import numpy as np
from py_scripts.consts import path_to_timetables_csv
from sqlalchemy_scripts.user_to_extra import Extra, Extra_to_User
from telegram.ext import ContextTypes
from telegram import Update


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


async def get_timetable_for_user_6_9(context: ContextTypes.DEFAULT_TYPE, class_):
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


async def get_timetable_for_user(context: ContextTypes.DEFAULT_TYPE, full_name, class_):
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


async def create_list_of_edits_lessons_for_student(df: pd.DataFrame, student_class):
    res = []
    for j in df.index.values:
        number_of_lesson = " ".join(df.iloc[j]['Урок №'].split('\n'))
        if 'Замены' in df.columns.values:
            if df.iloc[j]['Урок №'] == '' and j == 0:
                continue
            if student_class[:-1] in df.iloc[j]['Класс'] and (
                    student_class[-1].upper() in df.iloc[j]['Класс'].upper() or 'классы' in
                    df.iloc[j]['Класс'].lower()):
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
                                    cabinet,
                                    df.iloc[j][
                                        'Урок по расписанию']])  # Кабинет не указан, длина 5
                    else:
                        res.append([f"{class__}, ", number_of_lesson,
                                    subject + ', ' + cabinet, teacher,
                                    df.iloc[j][
                                        'Урок по расписанию']])  # Все указано, длина 5
                else:
                    tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                    res.append([f"{class__}, ", number_of_lesson,
                                subject + f"\n(Урок по расписанию: {tmp})"])  # Отмена урока, длина 3
        else:
            if student_class[:-1] in df.iloc[j]['Класс'] and (
                    student_class[-1].upper() in df.iloc[j]['Класс'].upper() or 'классы' in
                    df.iloc[j]['Класс'].lower()):
                class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                res.append([f"{class__}, ", number_of_lesson,
                            df.iloc[j]['Замены кабинетов'],
                            df.iloc[j][
                                'Урок по расписанию']])  # Изменения кабинетов, длина 4
    return sorted(res, key=lambda x: x[1])


async def get_edits_for_student(context: ContextTypes.DEFAULT_TYPE, student_class):
    t = ""
    edits_in_tt, for_which_day = await get_edits_in_timetable(context.user_data['NEXT_DAY_TT'])
    if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
            'сегодня' in for_which_day and not context.user_data.get('NEXT_DAY_TT')):
        if len(edits_in_tt) != 0:
            for df in edits_in_tt:
                sorted_res = await create_list_of_edits_lessons_for_student(df, student_class)
                text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n'
                flag = False
                for line in sorted_res:
                    flag = True
                    urok_po_rasp = " ".join(line[-1].split("\n"))
                    if len(line) == 3:
                        text += prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                    elif len(line) == 4:  # Замены каб.
                        if line[2] == urok_po_rasp == '':
                            text += prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                        else:
                            text += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                f'{urok_po_rasp})\n\n')
                    else:
                        text += prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                            f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                if flag:
                    t += for_which_day
                    t += text
    return t


async def get_standard_timetable_with_edits_for_student(context: ContextTypes.DEFAULT_TYPE, day_name, student_class, student_name, student_familia,
                                                        flag=True):
    if int(student_class[:-1]) >= 10:
        lessons, day = await get_standard_timetable_for_user(f'{student_familia} {student_name}',
                                                             student_class, days_from_short_text_to_num[day_name])
    else:
        lessons, day = await get_standard_timetable_for_user_6_9(student_class, days_from_short_text_to_num[day_name])
    txt = prepare_for_markdown((student_familia + ' ' + student_name + ' ' + student_class)
                               .strip(" "))
    if lessons.empty:
        class_txt = student_class
        return f'Ученика \"{txt}\" не найдено или отсутствует расписание для {class_txt} класса\.'
    app = f' для ученика {txt}'
    if not flag:
        app = ''
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*{app}\n\n'
    t = ""
    edits_text = ""
    context.user_data['NEXT_DAY_TT'] = False
    if days_from_short_text_to_num[day_name] == 0 and datetime.now().weekday() == 5:
        context.user_data['NEXT_DAY_TT'] = True
        edits_text = await get_edits_for_student(context, student_class)
    elif days_from_short_text_to_num[day_name] == datetime.now().weekday():
        context.user_data['NEXT_DAY_TT'] = False
        edits_text = await get_edits_for_student(context, student_class)
    elif days_from_short_text_to_num[day_name] == (datetime.now().weekday() + 1) % 7:
        context.user_data['NEXT_DAY_TT'] = True
        edits_text = await get_edits_for_student(context, student_class)
    for txt_info, key in lessons_keys.items():
        try:
            if int(student_class[:-1]) >= 10:
                pre_lesson_info = lessons.loc[key].split('###')
            else:
                pre_lesson_info = lessons.loc[key][day].split('###')

            t += prepare_for_markdown(txt_info)
            last_cab = ""
            for lesson_info in pre_lesson_info:
                lesson_info = lesson_info.split('\n')
                if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                                           'программирование (1)', 'практикум (2)', 'структуры данных (2)',
                                           'программирование (2)',
                                           'математика (1)', '(1)', 'физика (1)', 'эффекты (1)', 'математика (2)',
                                           'математике']:
                    if 'Эрлих И.Г.' in lesson_info[-1]:
                        lesson_info = ['Эрлих И.Г.'] + [lesson_info[-2]] + [lesson_info[-1].split(' ')[-1]]
                    lesson_name = lesson_info[-2]
                    teachers = " ".join(lesson_info[:-2])
                else:
                    if 'Эрлих И.Г.' in lesson_info[-1]:
                        lesson_info = ['Эрлих И.Г.'] + lesson_info[-3:-1] + [lesson_info[-1].split(' ')[-1]]
                    lesson_name = " ".join(lesson_info[-3:-1])
                    teachers = " ".join(lesson_info[:-3])
                cabinet = lesson_info[-1]
                if 'В' in lesson_name and 'Т' in lesson_name and 'Э.' in lesson_name and 'К.' in lesson_name or \
                        'В' in lesson_name and 'Т.' in lesson_name and 'Э.' in lesson_name and 'К' in lesson_name:
                    one_more_teacher_VTEK = (lesson_name.replace('В', '').replace('Т', '').
                                             replace('Э.', '.').replace('К.', '.').replace('Т.',
                                                                                           '.'))
                    cnt = sum([int(i in 'АБВГДЕËЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ') for i in
                               one_more_teacher_VTEK])
                    if cnt > 3:
                        one_more_teacher_VTEK = one_more_teacher_VTEK[:-1]
                    teachers += " " + one_more_teacher_VTEK
                    lesson_name = 'ВТЭК'
                elif lesson_name == 'И.Н. ВТЭК':
                    lesson_name = 'ВТЭК'
                    teachers += " И.Н."
                if len(lesson_info) == 2:
                    cabinet = last_cab
                    lesson_name = lesson_info[-1]
                    teachers = lesson_info[0]
                t += prepare_for_markdown(
                    f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')
                last_cab = cabinet
            t += '\n'
        except Exception as e:
            continue

    if edits_text:
        t = title + '_' + prepare_for_markdown(
            f'⚠️Обратите внимание, что для {student_class} ниже есть изменения в расписании!') + '_\n\n' + t + edits_text
    else:
        t = title + '\n' + t + edits_text
    return t


def extra_lessons_return(id, button_text):  # Кружки на день для ученика
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
            place = f"{extra.place} кабинет"
            if "зал" in extra.place or "online" in extra.place:
                place = extra.place
            text += f'🏫 Место проведения: {place} 🏫\n'
            full_text.append(text)
    return "".join(full_text)
