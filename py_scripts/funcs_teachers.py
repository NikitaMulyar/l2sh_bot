# -*- coding: utf-8 -*-
import pdfplumber
from py_scripts.consts import path_to_timetables, path_to_timetables_csv, lessons_keys, for_datetime, \
    days_from_num_to_full_text_formatted
import pandas as pd
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, get_edits_in_timetable, db_sess
import PyPDF2
import os
from datetime import datetime
from py_scripts.consts import days_from_num_to_full_text, days_from_short_text_to_num
from sqlalchemy_scripts.user_to_extra import Extra


async def create_list_of_edits_lessons_for_teacher(df):
    res = []
    for j in df.index.values:
        number_of_lesson = " ".join(df.iloc[j]['Урок №'].split('\n'))
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
                if cabinet.count('.') == 2 and 'зал' not in cabinet:
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
            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
            res.append([f"{class__}, ", number_of_lesson,
                        df.iloc[j]['Замены кабинетов'],
                        df.iloc[j]['Урок по расписанию']])  # Изменения кабинетов, длина 4
    return sorted(res, key=lambda x: x[1])


async def get_edits_for_teacher(context, surname, name):
    t = ""
    edits_in_tt, for_which_day = await get_edits_in_timetable(context.user_data['NEXT_DAY_TT'])
    if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
            'сегодня' in for_which_day and not context.user_data.get('NEXT_DAY_TT')):
        if len(edits_in_tt) != 0:
            for df in edits_in_tt:
                sorted_res = await create_list_of_edits_lessons_for_teacher(df)
                text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n\n'
                flag = False
                for line in sorted_res:
                    urok_po_rasp = " ".join(line[-1].split("\n"))
                    curr = ""
                    if len(line) == 3:
                        curr += prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                    elif len(line) == 4:  # Замены каб.
                        if line[2] == urok_po_rasp == '':
                            curr += prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                        else:
                            curr += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                f'{urok_po_rasp})\n\n')
                    else:
                        curr += prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                            f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                    if curr.strip(' '):
                        if surname.replace('ё', 'е') in curr.replace('ё', 'е') and \
                                name.replace('ё', 'е')[0] in curr.replace('ё', 'е'):
                            text += curr
                            flag = True
                if flag:
                    t += for_which_day
                    t += text
    return t


async def get_standard_timetable_with_edits_for_teacher(context, day, name, familia, flag=True):
    lessons, day = await get_standard_timetable_for_teacher(f'{familia} {name[0]}',
                                                            days_from_short_text_to_num[day])
    if lessons.empty:
        return f'В этот день нет уроков'
    app = f' для учителя {familia} {name}'
    if not flag:
        app = ''
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*{app}\n\n'
    t = ""
    edits_text = ""
    context.user_data['NEXT_DAY_TT'] = False
    if day == 0 and datetime.now().weekday() == 5:
        context.user_data['NEXT_DAY_TT'] = True
        edits_text = await get_edits_for_teacher(context, familia, name)
    elif day == datetime.now().weekday():
        context.user_data['NEXT_DAY_TT'] = False
        edits_text = await get_edits_for_teacher(context, familia, name)
    elif day == (datetime.now().weekday() + 1) % 7:
        context.user_data['NEXT_DAY_TT'] = True
        edits_text = await get_edits_for_teacher(context, familia, name)
    for txt_info, key in lessons_keys.items():
        try:
            pre_lesson_info = lessons.loc[key][1::]
            t += prepare_for_markdown(f'{txt_info}')
            for lesson_info in pre_lesson_info:
                lesson_info = lesson_info.split('\n')
                cabinet = lesson_info[-1]
                classes = ""
                lesson_name = []
                for el in lesson_info[:-1:]:
                    for grades in ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']:
                        if grades in el:
                            classes += el
                            break
                    else:
                        lesson_name.append(el)
                lesson_name = " ".join(lesson_name)
                t += prepare_for_markdown(
                    f'{lesson_name} - каб. {cabinet}\n(классы: {classes})\n')
            t += '\n'
        except Exception as e:
            continue
    if edits_text:
        t = title + '_' + prepare_for_markdown(
            '⚠️Обратите внимание, что у Вас есть изменения в расписании!\n\n') + '_' + t + edits_text
    else:
        t = title + '\n' + t + edits_text
    return t


async def extract_timetable_for_teachers():
    def get_all_teachers():
        reader = PyPDF2.PdfReader(f"{path_to_timetables}teachers.pdf")
        i = -1
        for page in reader.pages:
            i += 1
            info = page.extract_text().split('\n')[-1].split()
            info[2] = info[2][0]
            yield " ".join(info[1:3]), i

    async def save_timetable_csv(full_name, page_n):
        with pdfplumber.open(f"{path_to_timetables}teachers.pdf") as pdf:
            page = pdf.pages[page_n]
            table = page.extract_table()
            try:
                df = pd.DataFrame(table[1:], columns=table[0])
                for col in df.columns.values:
                    df.loc[df[col] == '', col] = '--'
            except Exception:
                df = pd.DataFrame(table[2:], columns=table[1])
                for col in df.columns.values:
                    df.loc[df[col] == '', col] = '--'
            df.ffill(axis=0, inplace=True)
            df.to_csv(path_to_timetables_csv + f'{full_name}.csv')
            with open('list_new_timetable.txt', mode='a', encoding='utf-8') as f:
                f.write(f'{full_name}\n')
            f.close()
        pdf.close()

    for teacher, page_n in list(get_all_teachers()):
        await save_timetable_csv(teacher, page_n)


async def get_timetable_for_teacher(context, full_name):
    if not os.path.exists(path_to_timetables_csv + f'{full_name}.csv'):
        return pd.DataFrame(), -1
    now_ = datetime.now()
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_teacher_timetable_for_day(0, full_name)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_teacher_timetable_for_day(day, full_name)
    if timetable_.empty:
        return timetable_, day
    last_les_end_h, last_les_end_m = map(int,
                                         timetable_.index.values[-1].split(' - ')[-1]
                                         .split(':'))
    h, m = now_.hour, now_.minute
    if (h, m) > (last_les_end_h, last_les_end_m):
        context.user_data['NEXT_DAY_TT'] = True
        if day == 5:
            timetable_, day = await extract_teacher_timetable_for_day(0, full_name)
            return timetable_, 0
        timetable_, day = await extract_teacher_timetable_for_day(day + 1, full_name)
        # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
    else:
        context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


async def get_standard_timetable_for_teacher(full_name, day):
    if not os.path.exists(path_to_timetables_csv + f'{full_name}.csv'):
        return pd.DataFrame(), -1
    timetable_, day = await extract_teacher_timetable_for_day(day, full_name)
    return timetable_, day


async def extract_teacher_timetable_for_day(day, full_name):
    df = pd.read_csv(path_to_timetables_csv + f'{full_name}.csv')
    df.drop('Unnamed: 0', axis=1, inplace=True)
    day2 = days_from_num_to_full_text[day]
    df = df[['Unnamed: 1', day2]]
    df = df[df[day2] != '--']
    df = df.set_index(df['Unnamed: 1'].values)
    return df, day


async def timetable_teacher_for_each_day(update, context, user):
    lessons, day = await get_timetable_for_teacher(context, f'{user.surname} {user.name[0]}')
    if lessons.empty:
        await update.message.reply_text(f'На {days_from_num_to_full_text_formatted[day]} у Вас нет уроков')
        return
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*\n\n'
    t = ""
    time_now = datetime.now()  # - timedelta(hours=3)
    for txt_info, key in lessons_keys.items():
        try:
            pre_lesson_info = lessons.loc[key][1::]
            start, end = for_datetime[key]
            if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}')
            else:
                t += prepare_for_markdown(f'{txt_info}')
            for lesson_info in pre_lesson_info:
                lesson_info = lesson_info.split('\n')
                cabinet = lesson_info[-1]
                classes = ""
                lesson_name = []
                for el in lesson_info[:-1:]:
                    for grades in ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']:
                        if grades in el:
                            classes += el
                            break
                    else:
                        lesson_name.append(el)
                lesson_name = " ".join(lesson_name)
                t += prepare_for_markdown(
                    f'{lesson_name} - каб. {cabinet}\n(классы: {classes})\n')
            if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                t += '*_'
            t += '\n'
        except Exception as e:
            continue
    edits_text = await get_edits_for_teacher(context, user.surname, user.name)
    if edits_text:
        t = title + '_' + prepare_for_markdown(
            '⚠️Обратите внимание, что у Вас есть изменения в расписании!\n\n') + '_' + t + edits_text
    else:
        t = title + '\n' + t
    await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())


def extra_lessons_teachers_return(button_text, surname):  # Кружки на день для учителя
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    extra_lessons = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), day == Extra.day).all()
    full_text = []
    extra_was = []
    for extra_lesson in extra_lessons:
        if extra_lesson.title in extra_was:
            continue
        text = "⤵️\n"
        ex = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), Extra.title == extra_lesson.title,
                                         Extra.time == extra_lesson.time).all()
        classes = []
        for el in ex:
            if str(el.grade) not in classes:
                classes.append(str(el.grade))
        extra_was.append(extra_lesson.title)
        text += f"📚 {extra_lesson.title} ({'/'.join(classes)} класс)📚\n"
        text += f"🕝 {extra_lesson.time} 🕝\n"
        place = ""
        if "зал" in extra_lesson.place or "online" in extra_lesson.place:
            place = extra_lesson.place
        else:
            place = f"{extra_lesson.place} кабинет"
        text += f'🏫 Место проведения: {place} 🏫\n'
        full_text.append(text)
    return "".join(full_text)
