from funcs_back import *
from telegram.ext import ConversationHandler


class GetTimetable:
    days = {0: 'Понедельник', 1: 'Вторник', 2: 'Среду', 3: 'Четверг', 4: 'Пятницу', 5: 'Субботу'}
    days2 = {0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг', 4: 'Пятница', 5: 'Суббота'}
    day_num = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5}
    lessons_keys = {'0️⃣-й урок, 8:30 - 8:55:\n': '0\n08:30 - 08:55',
                    '1️⃣-й урок, 9:00 - 9:45:\n': '1\n09:00 - 09:45',
                    '2️⃣-й урок, 9:55 - 10:40:\n': '2\n09:55 - 10:40',
                    '3️⃣-й урок, 10:50 - 11:35:\n': '3\n10:50 - 11:35',
                    '4️⃣-й урок, 11:45 - 12:30:\n': '4\n11:45 - 12:30',
                    '5️⃣-й урок, 12:50 - 13:35:\n': '5\n12:50 - 13:35',
                    '6️⃣-й урок, 13:55 - 14:40:\n': '6\n13:55 - 14:40',
                    '7️⃣-й урок, 14:50 - 15:35:\n': '7\n14:50 - 15:35',
                    '8️⃣-й урок, 15:45 - 16:30:\n': '8\n15:45 - 16:30'}
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

    async def get_edits(self, context, user):
        t = ""
        edits_in_tt, for_which_day = await get_edits_in_timetable(context.user_data['NEXT_DAY_TT'])
        if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
                'сегодня' in for_which_day and not context.user_data.get('NEXT_DAY_TT')):
            if len(edits_in_tt) != 0:
                for df in edits_in_tt:
                    res = []
                    for j in df.index.values:
                        if 'Замены' in df.columns.values:
                            if j == 0:
                                continue
                            if user.number in df.iloc[j]['Класс'] and user.grade[-1] in df.iloc[j][
                                'Класс']:
                                subject, teacher_cabinet = df.iloc[j]['Замены'].split('//')
                                subject = " ".join(subject.split('\n'))
                                class__ = "".join(df.iloc[j]['Класс'].split('\n'))
                                if teacher_cabinet != '':
                                    teacher_cabinet = teacher_cabinet.split('\n')
                                    cabinet = teacher_cabinet[-1]
                                    teacher = " ".join(teacher_cabinet[:-1])
                                    if cabinet.count('.') == 2:
                                        # Учитель
                                        res.append([f"{class__}, ", df.iloc[j]['№ урока'], subject,
                                                    cabinet,
                                                    df.iloc[j][
                                                        'Урок по расписанию']])  # Кабинет не указан, длина 5
                                    else:
                                        res.append([f"{class__}, ", df.iloc[j]['№ урока'],
                                                    subject + ', ' + cabinet, teacher,
                                                    df.iloc[j][
                                                        'Урок по расписанию']])  # Все указано, длина 5
                                else:
                                    res.append([f"{class__}, ", df.iloc[j]['№ урока'],
                                                subject])  # Отмена урока, длина 3
                        else:
                            if user.number in df.iloc[j]['Класс'] and user.grade[-1] in df.iloc[j][
                                'Класс']:
                                class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                                res.append([f"{class__}, ", df.iloc[j]['№ урока'],
                                            df.iloc[j]['Замены кабинетов'],
                                            df.iloc[j][
                                                'Урок по расписанию']])  # Изменения кабинетов, длина 4
                    sorted_res = sorted(res, key=lambda x: x[1])
                    text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n'
                    flag = False
                    for line in sorted_res:
                        flag = True
                        urok_po_rasp = " ".join(line[-1].split("\n"))
                        if len(line) == 3:
                            if 'отмена' in line[2].lower():
                                text += prepare_for_markdown(
                                    f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                            else:
                                text += prepare_for_markdown(
                                    f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                    f'{urok_po_rasp})\n\n')
                        elif len(line) == 4:  # Замены каб.
                            text += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                f'{urok_po_rasp})\n\n')
                        else:
                            text += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                                f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                    if flag:
                        t += for_which_day
                        t += text
        return t

    async def get_timetable(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполни свои данные: /start')
            return
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
            time_now = datetime.now()  # - timedelta(hours=3)
            # !!!!!!!!!!!!!!!!!
            for txt_info, key in self.lessons_keys.items():
                try:
                    if int(user.number) >= 10:
                        pre_lesson_info = lessons.loc[key]
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
                        if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                        'программирование (1)', 'практикум (2)', 'структуры данных (2)', 'программирование (2)',
                        'математика (1)', '(1)', 'физика (1)', 'эффекты (1)', 'математика (2)', 'математике']:
                            if lesson_info[-1] == 'Эрлих И.Г. 310':
                                lesson_info = ['Эрлих И.Г.'] + [lesson_info[-2]] + ['310']
                            lesson_name = lesson_info[-2]
                            teachers = " ".join(lesson_info[:-2])
                        else:
                            if lesson_info[-1] == 'Эрлих И.Г. 310':
                                lesson_info = ['Эрлих И.Г.'] + lesson_info[-3:-1] + ['310']
                            lesson_name = " ".join(lesson_info[-3:-1])
                            teachers = " ".join(lesson_info[:-3])
                        cabinet = lesson_info[-1]
                        if 'В' in lesson_name and 'Т' in lesson_name and 'Э.' in lesson_name and 'К.' in lesson_name:
                            one_more_teacher_VTEK = (lesson_name.replace('В', '').replace('Т', '').
                                                     replace('Э.', '.').replace('К.', '.'))
                            teachers += " " + one_more_teacher_VTEK
                            lesson_name = 'ВТЭК'
                        elif lesson_name == 'И.Н. ВТЭК':
                            lesson_name = 'ВТЭК'
                            teachers += " И.Н."
                        t += prepare_for_markdown(
                            f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')
                    if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                        t += '*_'
                    t += '\n'
                except Exception as e:
                    continue
            t += '\n'
            t += await self.get_edits(context, user)
            await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        elif (not context.user_data.get('EXTRA_CLICKED') and
              update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
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
                        if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                        'программирование (1)', 'практикум (2)', 'структуры данных (2)', 'программирование (2)',
                        'математика (1)', '(1)', 'физика (1)', 'эффекты (1)', 'математика (2)', 'математике']:
                            if lesson_info[-1] == 'Эрлих И.Г. 310':
                                lesson_info = ['Эрлих И.Г.'] + [lesson_info[-2]] + ['310']
                            lesson_name = lesson_info[-2]
                            teachers = " ".join(lesson_info[:-2])
                        else:
                            if lesson_info[-1] == 'Эрлих И.Г. 310':
                                lesson_info = ['Эрлих И.Г.'] + lesson_info[-3:-1] + ['310']
                            lesson_name = " ".join(lesson_info[-3:-1])
                            teachers = " ".join(lesson_info[:-3])
                        cabinet = lesson_info[-1]
                        if 'В' in lesson_name and 'Т' in lesson_name and 'Э.' in lesson_name and 'К.' in lesson_name:
                            one_more_teacher_VTEK = (lesson_name.replace('В', '').replace('Т', '').
                                                     replace('Э.', '.').replace('К.', '.'))
                            teachers += " " + one_more_teacher_VTEK
                            lesson_name = 'ВТЭК'
                        elif lesson_name == 'И.Н. ВТЭК':
                            lesson_name = 'ВТЭК'
                            teachers += " И.Н."
                        t += prepare_for_markdown(
                            f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')
                        """if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                        'программирование (1)', 'практикум (2)', 'структуры данных (2)', 'программирование (2)',
                        'математика (1)', '(1)', 'физика (1)', 'эффекты (1)', 'математика (2)', 'математике']:
                            t += prepare_for_markdown(
                                f'{lesson_info[-2]} - каб. {lesson_info[-1]}\n(учитель: {" ".join(lesson_info[:-2])})\n')
                        else:
                            t += prepare_for_markdown(
                                f'{" ".join(lesson_info[-3:-1])} - каб. {lesson_info[-1]}\n(учитель: {" ".join(lesson_info[:-3])})\n')"""
                    t += '\n'
                except Exception as e:
                    continue
            if self.day_num[update.message.text] == datetime.now().weekday():
                context.user_data['NEXT_DAY_TT'] = False
                t += await self.get_edits(context, user)
            elif self.day_num[update.message.text] == datetime.now().weekday() + 1:
                context.user_data['NEXT_DAY_TT'] = True
                t += await self.get_edits(context, user)
            await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        elif update.message.text == '🎨Мои кружки🎨':
            await update.message.reply_text('Выбери интересующий тебя день',
                                            reply_markup=await extra_school_timetable_kbrd())
            context.user_data['EXTRA_CLICKED'] = True
        elif context.user_data['EXTRA_CLICKED'] and update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
            context.user_data['EXTRA_CLICKED'] = False
            extra_text = extra_lessons_return(update.message.from_user.id, update.message.text)
            text = prepare_for_markdown(extra_text)
            if text == '':
                await update.message.reply_text(
                    f'*Кружков на {self.days[self.day_num[update.message.text]].lower()} нет*',
                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                return
            await update.message.reply_text(
                f'*Кружки на {self.days[self.day_num[update.message.text]].lower()}*\n\n{text}',
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        elif update.message.text == '♟️Сегодня♟️':
            today = datetime.now().weekday()
            context.user_data['EXTRA_CLICKED'] = False
            if today == 6:
                await update.message.reply_text(f'*В воскресенье нужно отдыхать\! Кружков нет\.*',
                                                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                return
            days = {value: key for key, value in self.day_num.items()}
            extra_text = extra_lessons_return(update.message.from_user.id, days[today])
            text = prepare_for_markdown(extra_text)
            if text == '':
                await update.message.reply_text(
                    f'*Кружков на {self.days[today].lower()} нет*',
                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                return
            await update.message.reply_text(
                f'*Кружки на {self.days[today].lower()}*\n\n{text}',
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        elif update.message.text == '🎭Все кружки🎭':
            context.user_data['EXTRA_CLICKED'] = False
            text_res = ""
            for day, day_number in self.day_num.items():
                extra_text = extra_lessons_return(update.message.from_user.id, day)
                text = prepare_for_markdown(extra_text)
                if text != "":
                    text_res += f'_*{self.days2[day_number]}*_\n{text}\n'
            if text_res == '':
                await update.message.reply_text(
                    f'*Ты еще не записывался\(лась\) на кружки\.*',
                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                return
            await update.message.reply_text(text_res,
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
