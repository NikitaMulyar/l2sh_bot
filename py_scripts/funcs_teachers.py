# -*- coding: utf-8 -*-
import pdfplumber

from py_scripts.class_extra_lesson import extra_send_near, extra_send_day
from py_scripts.consts import path_to_timetables, path_to_timetables_csv, lessons_keys, for_datetime, \
    days_from_num_to_full_text_formatted
import pandas as pd
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, db_sess
import PyPDF2
import os
from datetime import datetime
from sqlalchemy_scripts.extra_lessons import Extra
from sqlalchemy_scripts.users import User
from py_scripts.consts import days_from_num_to_full_text, days_from_short_text_to_num


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


async def timetable_teacher_for_each_day(context, user, update, edits_text, near=False):
    if near:
        lessons, day = await get_timetable_for_teacher(context, f'{user.surname} {user.name[0]}')
    else:
        lessons, day = await get_standard_timetable_for_teacher(f'{user.surname} {user.name[0]}',
                                                                days_from_short_text_to_num[
                                                                    update.message.text])
    if lessons.empty:
        if near:
            await update.message.reply_text(f'На {days_from_num_to_full_text_formatted[day]} у Вас нет уроков')
        else:
            await update.message.reply_text(f'В этот день у Вас нет уроков')
            if near:
                await extra_send_near(update, context, flag=True)
            else:
                await extra_send_day(update, flag=True)
        return
    title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*\n\n'
    t = ""
    if near:
        time_now = datetime.now()  # - timedelta(hours=3)
    for txt_info, key in lessons_keys.items():
        try:
            pre_lesson_info = lessons.loc[key][1::]
            if near:
                start, end = for_datetime[key]
                if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                    t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}')
                else:
                    t += prepare_for_markdown(f'{txt_info}')
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
            if near and start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                t += '*_'
            t += '\n'
        except Exception as e:
            continue
    if edits_text:
        t = title + '_' + prepare_for_markdown(
            '⚠️Обратите внимание, что у Вас есть изменения в расписании!\n\n') + '_' + t + edits_text
    else:
        t = title + '\n' + t + edits_text
    await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
    ######Вывод кружков вместе с расписанием
    if near:
        await extra_send_near(update, context, flag=True)
    else:
        await extra_send_day(update, flag=True)
    ####################
