# -*- coding: utf-8 -*-
import asyncio

import numpy as np
import telegram
import PyPDF2
from funcs_back import *
from datetime import datetime
from consts import *
import pandas as pd
import pdfplumber
import os


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


async def extract_timetable_for_day(day, pdf, page_n, class__):
    page = pdf.pages[page_n]
    table = page.extract_table()
    df = pd.DataFrame(table[1:], columns=table[0])
    for col in df.columns.values:
        df.loc[df[col] == '', col] = '--'
    df.ffill(axis=1, inplace=True)
    df = df.iloc[day].to_frame()
    df = df[df[day] != '--'][day]
    return df, day


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
            timetable_, day = await extract_timetable_for_day(day + 1, pdf, page_n, )
            context.user_data['NEXT_DAY_TT'] = True
            # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
    return timetable_, day










async def get_number_of_students_page_6_9(class_):
    if not os.path.exists(path_to_timetables + '6-9.pdf'):
        return -1
    reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
    page_n = 0
    for page in reader.pages:
        if class_ in page.extract_text():
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
    return timetable_, day


"""if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                            t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})') + '*_\n\n'
                        else:
                            t += prepare_for_markdown(f'{txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})\n\n')
                    else:
                        for lesson_info in pre_lesson_info:
                            if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                                t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})') + '*_\n\n'
                            else:
                                t += prepare_for_markdown(f'{txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})\n\n')"""


# print(asyncio.run(get_timetable_for_user_6_9(dict(), '6А'))[0].loc['1\n09:00 - 09:45'][2])


from datetime import datetime
time_ = datetime.now()
day_ = str(time_.day).rjust(2, '0')
month_ = str(time_.month).rjust(2, '0')
today_file = f'{day_}{month_}{time_.year}'
time_ = time_ + timedelta(days=1)
day_ = str(time_.day).rjust(2, '0')
month_ = str(time_.month).rjust(2, '0')
tomorrow_file = f'{day_}{month_}{time_.year}'
print(today_file, tomorrow_file)