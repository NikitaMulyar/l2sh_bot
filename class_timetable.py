import pandas as pd

from funcs_back import *
from telegram.ext import ConversationHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup
from consts import *


class GetTimetable:
    days = {0: 'Понедельник', 1: 'Вторник', 2: 'Среду', 3: 'Четверг', 4: 'Пятницу', 5: 'Субботу'}
    lessons_keys = {'0-й урок, 8:30 - 8:55:\n': '0\n08:30 - 08:55',
                    '1-й урок, 9:00 - 9:45:\n': '1\n09:00 - 09:45',
                    '2-й урок, 9:55 - 10:40:\n': '2\n09:55 - 10:40',
                    '3-й урок, 10:50 - 11:35:\n': '3\n10:50 - 11:35',
                    '4-й урок, 11:45 - 12:30:\n': '4\n11:45 - 12:30',
                    '5-й урок, 12:50 - 13:35:\n': '5\n12:50 - 13:35',
                    '6-й урок, 13:55 - 14:40:\n': '6\n13:55 - 14:40',
                    '7-й урок, 14:50 - 15:35:\n': '7\n14:50 - 15:35',
                    '8-й урок, 15:45 - 16:30:\n': '8\n15:45 - 16:30'}
    for_datetime = {'0\n08:30 - 08:55': ((8, 30),
                                         (8, 55)),
                    '1\n09:00 - 09:45': ((8, 55),
                                         (9, 55)),
                    '2\n09:55 - 10:40': ((9, 55),
                                         (10, 50)),
                    '3\n10:50 - 11:35': ((10, 50),
                                         (11, 45)),
                    '4\n11:45 - 12:30': ((11, 45),
                                         (12, 50)),
                    '5\n12:50 - 13:35': ((12, 50),
                                         (13, 55)),
                    '6\n13:55 - 14:40': ((13, 55),
                                         (14, 50)),
                    '7\n14:50 - 15:35': ((14, 50),
                                         (15, 45)),
                    '8\n15:45 - 16:30': ((15, 45),
                                         (16, 30))}

    async def timetable_kbrd(self):
        btn = KeyboardButton('📚Расписание📚')
        kbd = ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
        return kbd

    async def get_timetable(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        if context.user_data.get('last'):
            context.user_data['last'] = False
            return ConversationHandler.END
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполни свои данные')
            return ConversationHandler.END
        if update.message.text == '📚Расписание📚':
            user = db_sess.query(User).filter(User.telegram_id == user__id).first()
            lessons, day = await get_timetable_for_user(user.name, user.surname, user.grade)
            if lessons.empty:
                txt = (user.surname + ' ' + user.name + ' ' + user.grade)
                class_txt = user.grade
                await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                                f'расписание для {class_txt} класса.')
                return ConversationHandler.END
            t = f'*Расписание на {self.days[day]}*\n\n'
            time_now = datetime.now()
            for txt_info, key in self.lessons_keys.items():
                try:
                    lesson_info = lessons[key].split('\n')  # Получили информацию об уроке: учитель,
                    # предмет, каб.
                    start, end = self.for_datetime[key]
                    if start <= (time_now.hour, time_now.minute) < end:
                        t += f'_*' + prepare_for_markdown(
                            f'{txt_info}{lesson_info[1]} (Каб. {lesson_info[-1]}, учитель: {lesson_info[0]})') + '*_\n\n'
                    else:
                        t += prepare_for_markdown(
                            f'{txt_info}{lesson_info[1]} (Каб. {lesson_info[-1]}, учитель: {lesson_info[0]})\n\n')
                except Exception:
                    continue
            await update.message.reply_text(t, parse_mode='MarkdownV2')
            return ConversationHandler.END
        else:
            return ConversationHandler.END

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка расписаний завершена')
        return ConversationHandler.END

    async def load_timetables(self):
        pass
