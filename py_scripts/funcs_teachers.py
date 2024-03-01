# -*- coding: utf-8 -*-
import asyncio
from multiprocessing import Process

import pdfplumber
from py_scripts.consts import path_to_timetables, path_to_timetables_csv, lessons_keys, \
    for_datetime, days_from_num_to_full_text_formatted, days_from_full_text_to_num
import pandas as pd
from py_scripts.funcs_back import prepare_for_markdown, get_edits_in_timetable
import os
from datetime import datetime, timedelta
from py_scripts.consts import days_from_short_text_to_num
from telegram.ext import ContextTypes
from telegram import Update


async def create_list_of_edits_lessons_for_teacher(df: pd.DataFrame):
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
                                f'{cabinet} каб.', f"{df.iloc[j]['Урок по расписанию']} каб."])  # Кабинет не указан, длина 5
                else:
                    res.append([f"{class__}, ", number_of_lesson,
                                f'{subject}, {cabinet} каб.', teacher,
                                f"{df.iloc[j]['Урок по расписанию']} каб."])  # Все указано, длина 5
            else:
                tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                res.append([f"{class__}, ", number_of_lesson,
                            subject + f"\n(Урок по расписанию: {tmp} каб.)"])  # Отмена урока, длина 3
        else:
            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
            res.append([f"{class__}, ", number_of_lesson,
                        df.iloc[j]['Замены кабинетов'],
                        f"{df.iloc[j]['Урок по расписанию']} каб."])  # Изменения кабинетов, длина 4
    return sorted(res, key=lambda x: x[1])


async def get_edits_for_teacher(surname, name, date):
    result0 = []
    edits_in_tt, for_which_day = await get_edits_in_timetable(date)
    title_added = False
    if len(edits_in_tt) != 0:
        for df in edits_in_tt:
            sorted_res = await create_list_of_edits_lessons_for_teacher(df)
            result = [f'_{prepare_for_markdown(df.columns.values[-1])}_\n']
            flag = False
            for line in sorted_res:
                urok_po_rasp = " ".join(line[-1].split("\n"))
                if len(line) == 3:
                    curr = prepare_for_markdown(
                        f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                elif len(line) == 4:  # Замены каб.
                    if line[2] == urok_po_rasp == '':
                        curr = prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                    else:
                        curr = prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                            f'{urok_po_rasp})\n\n')
                else:
                    curr = prepare_for_markdown(
                        f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                        f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                curr = curr.replace('ё', 'е')
                if surname.replace('ё', 'е') in curr and name.replace('ё', 'е')[0] in curr:
                    result.append(curr)
                    flag = True
            if flag:
                if not title_added:
                    result0.append(for_which_day)
                    title_added = True
                result0.extend(result)
    return result0


async def get_standard_timetable_with_edits_for_teacher(day_name, name, familia, flag=True):
    day_code = days_from_short_text_to_num[day_name]
    lessons, day = await get_standard_timetable_for_teacher(f'{familia} {name[0]}',
                                                            day_code)
    app = prepare_for_markdown(f' для учителя {familia} {name}')
    t_app = (f'⚠️ _Обратите внимание\, что у учителя {prepare_for_markdown(familia)} '
             f'{prepare_for_markdown(name)} есть изменения в расписании\!_')
    if not flag:
        app = ''
        t_app = '⚠️ _Обратите внимание\, что у Вас есть изменения в расписании\!_'
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day_code]}_*{app}'
    t = ""
    today = datetime.now()
    plus_days = (7 - today.weekday() + day_code) % 7
    date_future = datetime.now() + timedelta(days=plus_days)
    day_ = str(date_future.day).rjust(2, '0')
    month_ = str(date_future.month).rjust(2, '0')
    date = f'{day_}.{month_}.{date_future.year}'
    edits_text = await get_edits_for_teacher(familia, name, date)
    for txt_info, key in lessons_keys.items():
        if key not in lessons.index.values:
            continue
        lesson_info = lessons.loc[key]
        t = "".join([t, prepare_for_markdown(txt_info)])

        lesson_info = lesson_info.split('\n')
        lesson_name = lesson_info[1]
        classes = lesson_info[0]
        cabinet = lesson_info[2]
        t = "".join([t, prepare_for_markdown(
            f'{lesson_name} - каб. {cabinet}\n(классы: {classes})\n')])
        t = f'{t}\n'
    if edits_text:
        t = "\n\n".join([title, t_app, t])
        t = (t, edits_text)
    elif not lessons.empty:
        t = ("\n\n".join([title, t]),)
    else:
        t = ('В этот день нет уроков\.',)
    return t


async def get_timetable_for_teacher(context: ContextTypes.DEFAULT_TYPE, full_name):
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
    df.drop(['Unnamed: 0'], axis=1, inplace=True)
    df = df.iloc[day].to_frame()
    df.dropna(axis=0, inplace=True)
    return df[day], day


async def timetable_teacher_for_each_day(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    lessons, day = await get_timetable_for_teacher(context, f'{user.surname} {user.name[0]}')
    if day != -1:
        title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*'
        t = ""
        time_now = datetime.now()  # - timedelta(hours=3)
        for txt_info, key in lessons_keys.items():
            if key not in lessons.index.values:
                continue
            lesson_info = lessons.loc[key]
            start, end = for_datetime[key]
            if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                t = "".join([t, '_*', prepare_for_markdown(f'➡️ {txt_info}')])
            else:
                t = "".join([t, prepare_for_markdown({txt_info})])
            lesson_info = lesson_info.split('\n')
            lesson_name = lesson_info[1]
            classes = lesson_info[0]
            cabinet = lesson_info[2]
            t = "".join([t, prepare_for_markdown(
                f'{lesson_name} - каб. {cabinet}\n(классы: {classes})\n')])
            if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                t = f'{t}*_'
            t = f'{t}\n'
        t = f'{t}\n'
    edits_text = await get_edits_for_teacher(context, user.surname, user.name)
    if edits_text and not lessons.empty:
        t = "\n\n".join([title, '⚠️ _Обратите внимание\, что у Вас есть изменения в расписании\!_',
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
    elif edits_text and day == -1:
        t = '⚠️ _Обратите внимание\, что у Вас есть изменения в расписании\!_\n\n'
        total_len = len(t)
        ind = 0
        while ind < len(edits_text) and total_len + len(edits_text[ind]) < 4000:
            total_len += len(edits_text[ind])
            ind += 1
        await update.message.reply_text("".join([t, "".join(edits_text[:ind])]), parse_mode='MarkdownV2')
        scnd = "".join(edits_text[ind:])
        if scnd:
            await update.message.reply_text(scnd, parse_mode='MarkdownV2')
    elif not lessons.empty:
        t = "".join([title, '\n\n', t])
        await update.message.reply_text(t, parse_mode='MarkdownV2')
    else:
        t = 'В ближайшие дни у Вас нет уроков\.'
        await update.message.reply_text(t, parse_mode='MarkdownV2')


def partition_teachers_data(st, end):
    async def put_teacher_data(page: pdfplumber.pdf.Page, i):
        info = page.extract_text().split('\n')[1].split()
        return "".join([info[1], ' ', info[2][0]]).replace('ё', 'e'), i

    async def save_timetable_csv(full_name, page: pdfplumber.pdf.Page):
        table = page.extract_table()[1:]
        df = pd.DataFrame(table[1:], columns=table[0])
        df = df.set_index(['']).transpose()
        df.index = [days_from_full_text_to_num[el] for el in df.index.values]
        df = df.ffill(axis=1)
        df.to_csv(path_to_timetables_csv + f'{full_name}.csv')

    async def main_():
        pages = pdfplumber.open(path_to_timetables + 'teachers.pdf').pages
        tasks = [put_teacher_data(pages[i], i) for i in range(st, end)]
        res = await asyncio.gather(*tasks)
        tasks = [save_timetable_csv(name, pages[page_n]) for name, page_n in res]
        await asyncio.gather(*tasks)
        all_ = []
        for name, i in res:
            all_.append("".join([name, '\n']))
        with open('bot_files/list_new_timetable.txt', mode='a', encoding='utf-8') as f:
            f.writelines(all_)
        f.close()

    asyncio.run(main_())


async def extract_timetable_for_teachers(updating=False):
    if not os.path.exists(path_to_timetables + 'teachers.pdf'):
        if updating:
            print(f'\033[31mTeachers\' timetables not found.\033[0m')
        return

    if updating:
        print('\033[33mTeachers\' timetables are processing.\033[0m')

    time_start = datetime.now()

    pdf = pdfplumber.open(path_to_timetables + 'teachers.pdf')
    TOTAL_PAGES = len(pdf.pages)
    PARTS = 3
    k = TOTAL_PAGES // PARTS
    intervals = [(k * i, k * (i + 1)) for i in range(PARTS)]
    intervals[-1] = (k * (PARTS - 1), TOTAL_PAGES)
    p1 = Process(target=partition_teachers_data, args=(*intervals[0],), daemon=True)
    p2 = Process(target=partition_teachers_data, args=(*intervals[1],), daemon=True)
    p3 = Process(target=partition_teachers_data, args=(*intervals[2],), daemon=True)
    #p4 = Process(target=partition_teachers_data, args=(*intervals[3],), daemon=True)
    p1.start()
    p2.start()
    p3.start()
    #p4.start()
    p1.join()
    p2.join()
    p3.join()
    #p4.join()

    time_end = datetime.now()

    if updating:
        print(f'\033[32mTeachers\' timetables are processed successfully.\033[0m')
    print(f'Processed time: {(time_end - time_start).total_seconds()} seconds')
    pdf.close()
