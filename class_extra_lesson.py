import pandas as pd
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from funcs_back import *
from data.extra_lessons import *


class Extra_Lessons:
    def __init__(self):
        days = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота"}
        db_sess = db_session.create_session()
        for i in range(6):
            extra_lessons = pd.read_excel('extra.xlsx', sheet_name=i, usecols=[2, 4, 6, 8, 10, 12]).values
            length = len(extra_lessons)
            for j in range(6):
                k = 1
                while k <= length:
                    if not pd.isnull(extra_lessons[k][j]):
                        title = extra_lessons[k][j]
                        place = extra_lessons[k + 4][j]
                        for l in range(1, 4):
                            if not pd.isnull(extra_lessons[k + l][j]):
                                if ("-" in extra_lessons[k + l][j] and "." in extra_lessons[k + l][j]) or (
                                        "переменах" in extra_lessons[k + l][j]):
                                    time = extra_lessons[k + l][j]
                                elif "Код" not in extra_lessons[k + l][j]:
                                    teacher = extra_lessons[k + l][j]
                        day = days[j]
                        extra = Extra(title=title, time=time, day=day, teacher=teacher, place=place, grade=i + 6)
                        db_sess.add(extra)
                    k += 6
        db_sess.commit()
        db_sess.close()

