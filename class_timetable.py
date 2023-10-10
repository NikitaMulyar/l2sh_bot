from funcs_back import *
from telegram.ext import ConversationHandler


class GetTimetable:
    days = {0: 'Понедельник', 1: 'Вторник', 2: 'Среду', 3: 'Четверг', 4: 'Пятницу', 5: 'Субботу'}
    day_num = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5}
    lessons_keys = {'0-й урок, 8:30 - 8:55:\n': '0\n08:30 - 08:55',
                    '1-й урок, 9:00 - 9:45:\n': '1\n09:00 - 09:45',
                    '2-й урок, 9:55 - 10:40:\n': '2\n09:55 - 10:40',
                    '3-й урок, 10:50 - 11:35:\n': '3\n10:50 - 11:35',
                    '4-й урок, 11:45 - 12:30:\n': '4\n11:45 - 12:30',
                    '5-й урок, 12:50 - 13:35:\n': '5\n12:50 - 13:35',
                    '6-й урок, 13:55 - 14:40:\n': '6\n13:55 - 14:40',
                    '7-й урок, 14:50 - 15:35:\n': '7\n14:50 - 15:35',
                    '8-й урок, 15:45 - 16:30:\n': '8\n15:45 - 16:30'}
    for_datetime = {'0\n08:30 - 08:55': ((8, 20),
                                         (8, 55)),
                    '1\n09:00 - 09:45': ((8, 55),
                                         (9, 45)),
                    '2\n09:55 - 10:40': ((9, 45),
                                         (10, 40)),
                    '3\n10:50 - 11:35': ((10, 40),
                                         (11, 35)),
                    '4\n11:45 - 12:30': ((11, 35),
                                         (12, 30)),
                    '5\n12:50 - 13:35': ((12, 30),
                                         (13, 35)),
                    '6\n13:55 - 14:40': ((13, 35),
                                         (14, 40)),
                    '7\n14:50 - 15:35': ((14, 40),
                                         (15, 35)),
                    '8\n15:45 - 16:30': ((15, 35),
                                         (16, 30))}

    """async def create_standard_timetable(self, update, context, db_sess, user__id):
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        lessons, day = await get_timetable_for_user(context, user.name, user.surname, user.grade)
        if lessons.empty:
            txt = (user.surname + ' ' + user.name + ' ' + user.grade)
            class_txt = user.grade

            await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                            f'расписание для {class_txt} класса.')
            return ConversationHandler.END
        t = f'*Расписание на _{self.days[day]}_*\n\n'
        time_now = datetime.now()  # - timedelta(hours=3)
        # !!!!!!!!!!!!!!!!!
        for txt_info, key in self.lessons_keys.items():
            try:
                lesson_info = lessons[key].split('\n')  # Получили информацию об уроке: учитель,
                # предмет, каб.
                start, end = self.for_datetime[key]

                if start <= (time_now.hour, time_now.minute) < end and not context.user_data[
                    'NEXT_DAY_TT']:
                    t += f'_*' + prepare_for_markdown(
                        f'➡️ {txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})') + '*_\n\n'
                else:
                    t += prepare_for_markdown(
                        f'{txt_info}{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})\n\n')
            except Exception:
                continue"""

    async def get_timetable(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполни свои данные: /start')
            return ConversationHandler.END
        if update.message.text == '📚Расписание📚':
            user = db_sess.query(User).filter(User.telegram_id == user__id).first()
            context.user_data['NEXT_DAY_TT'] = False
            if int(user.number) >= 10:
                lessons, day = await get_timetable_for_user(context, user.name, user.surname, user.grade)
            else:
                lessons, day = await get_timetable_for_user_6_9(context, user.grade)
            if lessons.empty:
                txt = (user.surname + ' ' + user.name + ' ' + user.grade)
                class_txt = user.grade

                await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                                f'расписание для {class_txt} класса.')
                return
            t = f'*Расписание на _{self.days[day]}_*\n\n'
            time_now = datetime.now()
            # !!!!!!!!!!!!!!!!!
            for txt_info, key in self.lessons_keys.items():
                try:
                    if int(user.number) >= 10:
                        pre_lesson_info = lessons.loc[key].split('###')
                    else:
                        pre_lesson_info = lessons.loc[key][day].split('###')
                    start, end = self.for_datetime[key]
                    # Получили информацию об уроке: учитель, предмет, каб.
                    # if type(pre_lesson_info) == str:
                    #     pre_lesson_info = [pre_lesson_info]
                    if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                        t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}')
                    else:
                        t += prepare_for_markdown(f'{txt_info}')
                    for lesson_info in pre_lesson_info:
                        lesson_info = lesson_info.split('\n')
                        t += prepare_for_markdown(f'{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})\n')
                    if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                        t += '*_'
                    t += '\n'
                except Exception as e:
                    continue
            t += '\n'
            edits_in_tt, for_which_day = await get_edits_in_timetable()
            print(for_which_day, context.user_data['NEXT_DAY_TT'], len(edits_in_tt))
            if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
                    'сегодня' in for_which_day and not context.user_data['NEXT_DAY_TT']):
                if len(edits_in_tt) != 0:
                    for df in edits_in_tt:
                        res = []
                        for j in df.index.values:
                            if 'Замены' in df.columns.values:
                                if j == 0:
                                    continue
                                if user.number in df.iloc[j]['Класс'] and user.grade[-1] in df.iloc[j]['Класс']:
                                    subject, teacher_cabinet = df.iloc[j]['Замены'].split('//')
                                    subject = " ".join(subject.split('\n'))
                                    class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                                    if teacher_cabinet != '':
                                        teacher_cabinet = teacher_cabinet.split('\n')
                                        cabinet = teacher_cabinet[-1]
                                        teacher = " ".join(teacher_cabinet[:-1])
                                        if cabinet.count('.') == 2:
                                            # Учитель
                                            res.append([f"{class__}, ", df.iloc[j]['№ урока'], subject, cabinet])
                                        else:
                                            res.append([f"{class__}, ", df.iloc[j]['№ урока'], subject + ', ' + cabinet, teacher])
                                    else:
                                        res.append([f"{class__}, ", df.iloc[j]['№ урока'], subject])
                            else:
                                if user.number in df.iloc[j]['Класс'] and user.grade[-1] in df.iloc[j]['Класс']:
                                    class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                                    res.append([f"{class__}, ", df.iloc[j]['№ урока'], df.iloc[j]['Замены кабинетов']])
                        sorted_res = sorted(res, key=lambda x: x[1])
                        text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n'
                        flag = False
                        for line in sorted_res:
                            flag = True
                            if len(line) == 3:
                                text += prepare_for_markdown(f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                            else:
                                text += prepare_for_markdown(f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})\n\n')
                        if flag:
                            t += for_which_day
                            t += text
            await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        elif update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
            user = db_sess.query(User).filter(User.telegram_id == user__id).first()
            if int(user.number) >= 10:
                lessons, day = await get_standard_timetable_for_user(user.name, user.surname, user.grade,
                                                                     self.day_num[update.message.text])
            else:
                lessons, day = await get_standard_timetable_for_user_6_9(user.grade,
                                                                         self.day_num[update.message.text])
            if lessons.empty:
                txt = (user.surname + ' ' + user.name + ' ' + user.grade)
                class_txt = user.grade

                await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                                f'расписание для {class_txt} класса.')
                return ConversationHandler.END
            t = f'*Расписание на _{self.days[day]}_*\n\n'
            for txt_info, key in self.lessons_keys.items():
                try:
                    if int(user.number) >= 10:
                        pre_lesson_info = lessons.loc[key].split('###')
                    else:
                        pre_lesson_info = lessons.loc[key][day].split('###')

                    t += prepare_for_markdown(f'{txt_info}')
                    for lesson_info in pre_lesson_info:
                        lesson_info = lesson_info.split('\n')
                        t += prepare_for_markdown(
                            f'{lesson_info[1]} - каб. {lesson_info[-1]}\n(учитель: {lesson_info[0]})\n')
                    t += '\n'
                except Exception as e:
                    continue
            await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        elif update.message.text == '🎨Мои кружки🎨':
            await update.message.reply_text('Выбери интересующий тебя день',
                                            reply_markup=await extra_school_timetable_kbrd())
        elif update.message.text == '♟️Сегодня♟️':
            await update.message.reply_text('Кружки', reply_markup=await timetable_kbrd())
