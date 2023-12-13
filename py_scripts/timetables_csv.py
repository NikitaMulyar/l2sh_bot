# -*- coding: utf-8 -*-
import PyPDF2
from consts import *
import pandas as pd
import pdfplumber
import os
import numpy as np


async def extract_timetable_for_students_10_11(classes=None):
    def get_all_students_classes(classes):
        for i in range(len(classes)):
            classes[i] = classes[i] + '.pdf'
        for i in classes:
            reader = PyPDF2.PdfReader(path_to_timetables + i)
            for page in reader.pages:
                info = page.extract_text().split('\n')[-1].split()
                if len(info) == 4:
                    yield " ".join(info[2:]), info[0]
                else:
                    yield " ".join(info[2:-1]), info[0]

    def get_all_students():
        for i in os.listdir(path_to_timetables)[1:]:
            reader = PyPDF2.PdfReader(path_to_timetables + i)
            for page in reader.pages:
                info = page.extract_text().split('\n')[-1].split()
                if len(info) == 4:
                    yield " ".join(info[2:]), info[0]
                else:
                    yield " ".join(info[2:-1]), info[0]

    async def get_number_of_student_page(full_name, class_):
        if not os.path.exists(path_to_timetables + class_):
            return -1
        reader = PyPDF2.PdfReader(path_to_timetables + class_)
        page_n = 0
        for page in reader.pages:
            if full_name in page.extract_text():
                return page_n
            page_n += 1
        # 'Такой ученик не найден или для вашего класса нет расписания :('
        return -1

    async def save_timetable_csv(full_name, class_, page_n):
        with pdfplumber.open(path_to_timetables + class_ + '.pdf') as pdf:
            page = pdf.pages[page_n]
            table = page.extract_table()
            df = pd.DataFrame(table[1:], columns=table[0])
            for col in df.columns.values:
                df.loc[df[col] == '', col] = '--'
            df.ffill(axis=1, inplace=True)
            df.to_csv(path_to_timetables_csv + f'{full_name} {class_}.csv')

    if classes:
        for student in list(get_all_students_classes(classes)):
            page_n = await get_number_of_student_page(student[0], student[1] + '.pdf')
            if page_n != -1:
                await save_timetable_csv(student[0], student[1], page_n)
        return

    for student in list(get_all_students()):
        page_n = await get_number_of_student_page(student[0], student[1] + '.pdf')
        if page_n != -1:
            await save_timetable_csv(student[0], student[1], page_n)


async def extract_timetable_for_students_6_9():
    def get_all_classes():
        if not os.path.exists(path_to_timetables + '6-9.pdf'):
            return None
        i = os.listdir(path_to_timetables)[0]
        reader = PyPDF2.PdfReader(path_to_timetables + i)
        for page in reader.pages:
            info = page.extract_text().split('\n')[-1]
            yield info

    async def get_number_of_class_page(class_):
        reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
        page_n = 0
        for page in reader.pages:
            if class_ == page.extract_text().split('\n')[-1]:
                return page_n
            page_n += 1
        # 'Такой класс не найден или для вашего класса нет расписания :('
        return -1

    async def save_timetable_csv(class_, page_n):
        with pdfplumber.open(path_to_timetables + '6-9.pdf') as pdf:
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
            df.to_csv(path_to_timetables_csv + f'{class_}.csv')

    for class_ in list(get_all_classes()):
        page_n = await get_number_of_class_page(class_)
        if page_n != -1:
            await save_timetable_csv(class_, page_n)
