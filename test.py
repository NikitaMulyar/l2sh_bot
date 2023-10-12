from consts import *
import PyPDF2
import os
import sqlite3


async def get_number_of_students_page_6_9(class_):
    if not os.path.exists(path_to_timetables + '6-9.pdf'):
        return -1
    reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
    page_n = 0
    for page in reader.pages:
        if class_ == page.extract_text().split('\n')[-1]:
            break
        page_n += 1
    else:
        # 'Такой класс не найден или для вашего класса нет расписания :('
        return -1
    return page_n

def get_number_of_students_page():
    for i in os.listdir(path_to_timetables)[1:]:
        reader = PyPDF2.PdfReader(path_to_timetables + i)
        for page in reader.pages:
            info = page.extract_text().split('\n')[-1].split()
            yield " ".join(info[2:]), info[0]

async def get_number_of_students_page_6_9(class_):
    reader = PyPDF2.PdfReader(path_to_timetables + '6-9.pdf')
    page_n = 0
    for page in reader.pages:
        if class_ == page.extract_text().split('\n')[-1]:
            break
        page_n += 1
    else:
        # 'Такой класс не найден или для вашего класса нет расписания :('
        return -1
    return page_n


def get_all_classes():
    if not os.path.exists(path_to_timetables + '6-9.pdf'):
        return None
    i = os.listdir(path_to_timetables)[0]
    reader = PyPDF2.PdfReader(path_to_timetables + i)
    for page in reader.pages:
        info = page.extract_text().split('\n')[-1]
        yield info


print(list(get_all_classes()))


