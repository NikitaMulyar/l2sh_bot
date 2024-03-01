# -*- coding: utf-8 -*-
from datetime import datetime
import os
import asyncio

import numpy as np
import pandas as pd
import pdfplumber
from py_scripts.consts import path_to_timetables, path_to_timetables_csv, \
    days_from_short_text_to_num
from multiprocessing import Process


def partition_student_10_11_data(st, end):
    async def put_student_data(page: pdfplumber.pdf.Page, i):
        info = page.extract_text().split('\n')[1].split()
        if len(info) == 5:
            info = info[:-1]
        return " ".join([" ".join(info[2:]), info[0]]).replace('ё', 'е'), i

    async def save_timetable_csv(full_name, page: pdfplumber.pdf.Page):
        table = page.extract_table()[1:]
        df = pd.DataFrame(table[1:], columns=table[0])
        df.drop([''], axis=1, inplace=True)
        df = df.ffill(axis=1)
        df.to_csv(path_to_timetables_csv + f'{full_name}.csv')

    async def main_():
        pages = pdfplumber.open(path_to_timetables + '10-11.pdf').pages
        tasks = [put_student_data(pages[i], i) for i in range(st, end)]
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


async def extract_timetable_for_students_10_11(updating=False):
    if not os.path.exists(path_to_timetables + '10-11.pdf'):
        if updating:
            print(f'\033[31m10-11 grade students\' timetables not found.\033[0m')
        return

    if updating:
        print('\033[33m10-11 grade students\' timetables are processing.\033[0m')

    time_start = datetime.now()

    pdf = pdfplumber.open(path_to_timetables + '10-11.pdf')
    TOTAL_PAGES = len(pdf.pages)
    PARTS = 3
    k = TOTAL_PAGES // PARTS
    intervals = [(k * i, k * (i + 1)) for i in range(PARTS)]
    intervals[-1] = (k * (PARTS - 1), TOTAL_PAGES)
    p1 = Process(target=partition_student_10_11_data, args=(*intervals[0],), daemon=True)
    p2 = Process(target=partition_student_10_11_data, args=(*intervals[1],), daemon=True)
    p3 = Process(target=partition_student_10_11_data, args=(*intervals[2],), daemon=True)
    #p4 = Process(target=partition_student_10_11_data, args=(*intervals[3],), daemon=True)
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
        print(f'\033[32m10-11 grade students\' timetables are processed successfully.\033[0m')
    print(f'Processed time: {(time_end - time_start).total_seconds()} seconds')
    pdf.close()


def partition_student_6_9_data(st, end):
    async def put_class_data(page: pdfplumber.pdf.Page, i):
        info = page.extract_text().split('\n')[1]
        return info, i

    async def save_timetable_csv(class_, page: pdfplumber.pdf.Page):
        table = page.extract_table()[1:]
        df = pd.DataFrame(table[1:], columns=table[0])
        df[''].ffill(axis=0, inplace=True)
        df[''] = df[''].apply(lambda x: days_from_short_text_to_num[x])
        for col in df.columns.values:
            if col != '':
                df[col] = df[col] + '###'
        df = df.groupby('').sum()
        for col in df.columns.values:
            df[col] = df[col].apply(lambda x: np.NaN if x == 0 else x)
        df = df.ffill(axis=1)
        df.to_csv(path_to_timetables_csv + f'{class_}.csv')

    async def main_():
        pages = pdfplumber.open(path_to_timetables + '6-9.pdf').pages
        tasks = [put_class_data(pages[i], i) for i in range(st, end)]
        res = await asyncio.gather(*tasks)
        tasks = [save_timetable_csv(class_, pages[page_n]) for class_, page_n in res]
        await asyncio.gather(*tasks)
        all_ = []
        for class_, i in res:
            all_.append("".join([class_, '\n']))
        with open('bot_files/list_new_timetable.txt', mode='a', encoding='utf-8') as f:
            f.writelines(all_)
        f.close()

    asyncio.run(main_())


async def extract_timetable_for_students_6_9(updating=False):
    if not os.path.exists(path_to_timetables + '6-9.pdf'):
        if updating:
            print(f'\033[31m6-9 grade students\' timetables not found.\033[0m')
        return

    if updating:
        print('\033[33m6-9 grade students\' timetables are processing.\033[0m')

    time_start = datetime.now()

    pdf = pdfplumber.open(path_to_timetables + '6-9.pdf')
    TOTAL_PAGES = len(pdf.pages)
    PARTS = 3
    k = TOTAL_PAGES // PARTS
    intervals = [(k * i, k * (i + 1)) for i in range(PARTS)]
    intervals[-1] = (k * (PARTS - 1), TOTAL_PAGES)
    p1 = Process(target=partition_student_6_9_data, args=(*intervals[0],), daemon=True)
    p2 = Process(target=partition_student_6_9_data, args=(*intervals[1],), daemon=True)
    p3 = Process(target=partition_student_6_9_data, args=(*intervals[2],), daemon=True)
    #p4 = Process(target=partition_student_6_9_data, args=(*intervals[3],), daemon=True)
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
        print(f'\033[32m6-9 grade students\' timetables are processed successfully.\033[0m')
    print(f'Processed time: {(time_end - time_start).total_seconds()} seconds')
    pdf.close()


if __name__ == "__main__":
    asyncio.run(extract_timetable_for_students_10_11(updating=True))
    asyncio.run(extract_timetable_for_students_6_9(updating=True))
