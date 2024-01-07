# -*- coding: utf-8 -*-
import PyPDF2
from py_scripts.consts import path_to_timetables, path_to_timetables_csv
import pandas as pd
import pdfplumber
import os
import numpy as np
from py_scripts.consts import days_from_short_text_to_num


async def extract_timetable_for_students_10_11():
    def get_all_students():
        if not os.path.exists(path_to_timetables + '10-11.pdf'):
            return None
        reader = PyPDF2.PdfReader(path_to_timetables + '10-11.pdf')
        i = 0
        for page in reader.pages:
            info = page.extract_text().split('\n')[-1].split()
            if len(info) == 4:
                yield " ".join(info[2:]), info[0], i
            else:
                yield " ".join(info[2:-1]), info[0], i
            i += 1

    async def save_timetable_csv(full_name, class_, page_n):
        with pdfplumber.open(path_to_timetables + '10-11.pdf') as pdf:
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
            df.ffill(axis=1, inplace=True)
            df.to_csv(path_to_timetables_csv + f'{full_name} {class_}.csv')

    for student in list(get_all_students()):
        if student is None:
            continue
        await save_timetable_csv(student[0], student[1], student[2])


async def extract_timetable_for_students_6_9():
    def get_all_classes():
        if not os.path.exists(path_to_timetables + '6-9.pdf'):
            return None
        reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
        i = 0
        for page in reader.pages:
            info = page.extract_text().split('\n')[-1]
            yield info, i
            i += 1

    async def save_timetable_csv(class_, page_n):
        with pdfplumber.open(path_to_timetables + '6-9.pdf') as pdf:
            table = pdf.pages[page_n].extract_table()
            try:
                df = pd.DataFrame(table[1:], columns=table[0])
                df[''].ffill(axis=0, inplace=True)
                df[''] = df[''].apply(lambda x: days_from_short_text_to_num[x])
                for col in df.columns.values:
                    if col != '':
                        df[col] = df[col] + '###'
                df = df.groupby('').sum()
                for col in df.columns.values:
                    df[col] = df[col].apply(lambda x: np.NaN if x == 0 else x)
            except Exception:
                df = pd.DataFrame(table[2:], columns=table[1])
                df[''].ffill(axis=0, inplace=True)
                days_from_short_text_to_num = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5}
                df[''] = df[''].apply(lambda x: days_from_short_text_to_num[x])
                for col in df.columns.values:
                    if col != '':
                        df[col] = df[col] + '###'
                df = df.groupby('').sum()
                for col in df.columns.values:
                    df[col] = df[col].apply(lambda x: np.NaN if x == 0 else x)
            df = df.ffill(axis=1)
            df.to_csv(path_to_timetables_csv + f'{class_}.csv')

    for class_ in list(get_all_classes()):
        if class_ is None:
            continue
        await save_timetable_csv(class_[0], class_[1])
