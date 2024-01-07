from telegram import ReplyKeyboardMarkup

from py_scripts.funcs_back import prepare_for_markdown, get_standard_timetable_for_user, \
    get_standard_timetable_for_user_6_9, get_edits_in_timetable, timetable_kbrd, throttle2
from py_scripts.funcs_teachers import get_standard_timetable_for_teacher, extra_send_day
from telegram.ext import ConversationHandler
from datetime import datetime
from py_scripts.consts import days_from_num_to_full_text, days_from_short_text_to_num, lessons_keys


class GetTimetableForStudent:
    async def get_edits(self, context, student_class):
        t = ""
        edits_in_tt, for_which_day = await get_edits_in_timetable(context.user_data['NEXT_DAY_TT'])
        if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
                'сегодня' in for_which_day and not context.user_data.get('NEXT_DAY_TT')):
            if len(edits_in_tt) != 0:
                for df in edits_in_tt:
                    res = []
                    for j in df.index.values:
                        number_of_lesson = " ".join(df.iloc[j]['Урок №'].split('\n'))
                        if 'Замены' in df.columns.values:
                            if df.iloc[j]['Урок №'] == '' and j == 0:
                                continue
                            if student_class[:-1] in df.iloc[j]['Класс'].upper() and (
                                    student_class[-1] in df.iloc[j]['Класс'].upper() or 'классы' in df.iloc[j]['Класс'].lower()):
                                subject, teacher_cabinet = df.iloc[j]['Замены'].split('//')
                                subject = " ".join(subject.split('\n'))
                                class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                                if teacher_cabinet != '':
                                    teacher_cabinet = teacher_cabinet.split('\n')
                                    cabinet = teacher_cabinet[-1]
                                    teacher = " ".join(teacher_cabinet[:-1])
                                    if cabinet.count('.') == 2:
                                        # Учитель
                                        res.append([f"{class__}, ", number_of_lesson, subject,
                                                    cabinet,
                                                    df.iloc[j][
                                                        'Урок по расписанию']])  # Кабинет не указан, длина 5
                                    else:
                                        res.append([f"{class__}, ", number_of_lesson,
                                                    subject + ', ' + cabinet, teacher,
                                                    df.iloc[j][
                                                        'Урок по расписанию']])  # Все указано, длина 5
                                else:
                                    tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                                    res.append([f"{class__}, ", number_of_lesson,
                                                subject + f"\n(Урок по расписанию: {tmp})"])  # Отмена урока, длина 3
                        else:
                            if student_class[:-1] in df.iloc[j]['Класс'].upper() and (
                                    student_class[-1] in df.iloc[j]['Класс'].upper() or 'классы' in df.iloc[j]['Класс'].lower()):
                                class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                                res.append([f"{class__}, ", number_of_lesson,
                                            df.iloc[j]['Замены кабинетов'],
                                            df.iloc[j]['Урок по расписанию']])  # Изменения кабинетов, длина 4
                    sorted_res = sorted(res, key=lambda x: x[1])
                    text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n'
                    flag = False
                    for line in sorted_res:
                        flag = True
                        urok_po_rasp = " ".join(line[-1].split("\n"))
                        if len(line) == 3:
                            text += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                        elif len(line) == 4:  # Замены каб.
                            if line[2] == urok_po_rasp == '':
                                text += prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                            else:
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

    async def get_timetable(self, update, context, day_name, student_class, student_name, student_familia):
        if int(student_class[:-1]) >= 10:
            lessons, day = await get_standard_timetable_for_user(f'{student_familia} {student_name}',
                                                                 student_class, days_from_short_text_to_num[day_name])
        else:
            lessons, day = await get_standard_timetable_for_user_6_9(student_class, days_from_short_text_to_num[day_name])
        txt = (student_familia + ' ' + student_name + ' ' + student_class)
        if lessons.empty:
            class_txt = student_class
            await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                            f'расписание для {class_txt} класса.')
            return
        title = f'*Расписание на _{days_from_num_to_full_text[day]}_* для ученика {txt.strip(" ")}\n\n'
        t = ""
        edits_text = ""
        context.user_data['NEXT_DAY_TT'] = False
        if days_from_short_text_to_num[day_name] == 0 and datetime.now().weekday() == 5:
            context.user_data['NEXT_DAY_TT'] = True
            edits_text = await self.get_edits(context, student_class)
        elif days_from_short_text_to_num[day_name] == datetime.now().weekday():
            context.user_data['NEXT_DAY_TT'] = False
            edits_text = await self.get_edits(context, student_class)
        elif days_from_short_text_to_num[day_name] == (datetime.now().weekday() + 1) % 7:
            context.user_data['NEXT_DAY_TT'] = True
            edits_text = await self.get_edits(context, student_class)
        for txt_info, key in lessons_keys.items():
            try:
                if int(student_class[:-1]) >= 10:
                    pre_lesson_info = lessons.loc[key].split('###')
                else:
                    pre_lesson_info = lessons.loc[key][day].split('###')

                t += prepare_for_markdown(txt_info)
                last_cab = ""
                for lesson_info in pre_lesson_info:
                    lesson_info = lesson_info.split('\n')
                    if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                                               'программирование (1)', 'практикум (2)', 'структуры данных (2)',
                                               'программирование (2)',
                                               'математика (1)', '(1)', 'физика (1)', 'эффекты (1)', 'математика (2)',
                                               'математике']:
                        if 'Эрлих И.Г.' in lesson_info[-1]:
                            lesson_info = ['Эрлих И.Г.'] + [lesson_info[-2]] + [lesson_info[-1].split(' ')[-1]]
                        lesson_name = lesson_info[-2]
                        teachers = " ".join(lesson_info[:-2])
                    else:
                        if 'Эрлих И.Г.' in lesson_info[-1]:
                            lesson_info = ['Эрлих И.Г.'] + lesson_info[-3:-1] + [lesson_info[-1].split(' ')[-1]]
                        lesson_name = " ".join(lesson_info[-3:-1])
                        teachers = " ".join(lesson_info[:-3])
                    cabinet = lesson_info[-1]
                    if 'В' in lesson_name and 'Т' in lesson_name and 'Э.' in lesson_name and 'К.' in lesson_name or \
                            'В' in lesson_name and 'Т.' in lesson_name and 'Э.' in lesson_name and 'К' in lesson_name:
                        one_more_teacher_VTEK = (lesson_name.replace('В', '').replace('Т', '').
                                                 replace('Э.', '.').replace('К.', '.').replace('Т.',
                                                                                               '.'))
                        cnt = sum([int(i in 'АБВГДЕËЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ') for i in
                                   one_more_teacher_VTEK])
                        if cnt > 3:
                            one_more_teacher_VTEK = one_more_teacher_VTEK[:-1]
                        teachers += " " + one_more_teacher_VTEK
                        lesson_name = 'ВТЭК'
                    elif lesson_name == 'И.Н. ВТЭК':
                        lesson_name = 'ВТЭК'
                        teachers += " И.Н."
                    if len(lesson_info) == 2:
                        cabinet = last_cab
                        lesson_name = lesson_info[-1]
                        teachers = lesson_info[0]
                    t += prepare_for_markdown(
                        f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')
                    last_cab = cabinet
                t += '\n'
            except Exception as e:
                continue

        if edits_text:
            t = title + '_' + prepare_for_markdown(
                f'⚠️Обратите внимание, что для {student_class} ниже есть изменения в расписании!\n\n') + '_' + t + edits_text
        else:
            t = title + '\n' + t + edits_text
        await update.message.reply_text(t, parse_mode='MarkdownV2')


class GetTimetableForTeacher:
    async def get_edits_for_teacher(self, context, surname, name):
        t = ""
        edits_in_tt, for_which_day = await get_edits_in_timetable(context.user_data['NEXT_DAY_TT'])
        if ('завтра' in for_which_day and context.user_data['NEXT_DAY_TT'] or
                'сегодня' in for_which_day and not context.user_data.get('NEXT_DAY_TT')):
            if len(edits_in_tt) != 0:
                for df in edits_in_tt:
                    res = []
                    for j in df.index.values:
                        number_of_lesson = " ".join(df.iloc[j]['Урок №'].split('\n'))
                        if 'Замены' in df.columns.values:
                            if df.iloc[j]['Урок №'] == '' and j == 0:
                                continue
                            subject, teacher_cabinet = df.iloc[j]['Замены'].split('//')
                            subject = " ".join(subject.split('\n'))
                            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                            if teacher_cabinet != '':
                                teacher_cabinet = teacher_cabinet.split('\n')
                                cabinet = teacher_cabinet[-1]
                                teacher = " ".join(teacher_cabinet[:-1])
                                if cabinet.count('.') == 2 and 'зал' not in cabinet:
                                    # Учитель
                                    res.append([f"{class__}, ", number_of_lesson, subject,
                                                cabinet,
                                                df.iloc[j][
                                                    'Урок по расписанию']])  # Кабинет не указан, длина 5
                                else:
                                    res.append([f"{class__}, ", number_of_lesson,
                                                subject + ', ' + cabinet, teacher,
                                                df.iloc[j][
                                                    'Урок по расписанию']])  # Все указано, длина 5
                            else:
                                tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                                res.append([f"{class__}, ", number_of_lesson,
                                            subject + f"\n(Урок по расписанию: {tmp})"])  # Отмена урока, длина 3
                        else:
                            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                            res.append([f"{class__}, ", number_of_lesson,
                                        df.iloc[j]['Замены кабинетов'],
                                        df.iloc[j]['Урок по расписанию']])  # Изменения кабинетов, длина 4
                    sorted_res = sorted(res, key=lambda x: x[1])
                    text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n\n'
                    flag = False
                    for line in sorted_res:
                        urok_po_rasp = " ".join(line[-1].split("\n"))
                        curr = ""
                        if len(line) == 3:
                            curr += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                        elif len(line) == 4:  # Замены каб.
                            if line[2] == urok_po_rasp == '':
                                curr += prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                            else:
                                curr += prepare_for_markdown(
                                    f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                    f'{urok_po_rasp})\n\n')
                        else:
                            curr += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                                f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                        if curr.strip(' '):
                            if surname.replace('ё', 'е') in curr.replace('ё', 'е') and \
                                    name.replace('ё', 'е')[0] in curr.replace('ё', 'е'):
                                text += curr
                                flag = True
                    if flag:
                        t += for_which_day
                        t += text
        return t

    async def diff_teacher_timetable(self, update, context, day, name, familia):
        lessons, day = await get_standard_timetable_for_teacher(f'{familia} {name[0]}',
                                                                days_from_short_text_to_num[day])
        if lessons.empty:
            await update.message.reply_text(f'В этот день нет уроков')
            return
        title = f'*Расписание на _{days_from_num_to_full_text[day]}_*\n\n'
        t = ""
        edits_text = ""
        context.user_data['NEXT_DAY_TT'] = False
        if day == 0 and datetime.now().weekday() == 5:
            context.user_data['NEXT_DAY_TT'] = True
            edits_text = await self.get_edits_for_teacher(context, familia, name)
        elif day == datetime.now().weekday():
            context.user_data['NEXT_DAY_TT'] = False
            edits_text = await self.get_edits_for_teacher(context, familia, name)
        elif day == (datetime.now().weekday() + 1) % 7:
            context.user_data['NEXT_DAY_TT'] = True
            edits_text = await self.get_edits_for_teacher(context, familia, name)
        for txt_info, key in lessons_keys.items():
            try:
                pre_lesson_info = lessons.loc[key][1::]
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
        await extra_send_day(update, flag=True)
        ####################


class CheckStudentTT:
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД'] + ['Учитель']
    step_class = 1
    step_familia = 2
    step_name = 3
    step_date = 4
    get_tt = GetTimetableForStudent()
    get_teach = GetTimetableForTeacher()

    async def classes_buttons(self):
        classes = [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)] + [["Учитель"]]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True)
        return kbd

    async def days_buttons(self):
        arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
        kbd = ReplyKeyboardMarkup([arr], resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        await update.message.reply_text('С помощью этой команды можно быстро посмотреть расписание '
                                        'какого-то класса, ученика или учителя. Выберите из списка интересуемый класс.\n'
                                        'Прерваться: /end_check',
                                        reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update, context):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        context.user_data['INFO']['Class'] = update.message.text
        if "6" <= update.message.text[:-1] <= "9":
            kbrd = await self.days_buttons()
            await update.message.reply_text('Выберите день недели для расписания',
                                            reply_markup=kbrd)
            context.user_data['INFO']['Name'] = ''
            context.user_data['INFO']['Familia'] = ''
            return self.step_date
        await update.message.reply_text(f'Укажите фамилию учащегося (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update, context):
        context.user_data['INFO']['Familia'] = update.message.text
        await update.message.reply_text(f'Укажите ПОЛНОЕ имя учащегося (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        kbrd = await self.days_buttons()
        await update.message.reply_text('Выберите день недели для расписания',
                                        reply_markup=kbrd)
        return self.step_date

    @throttle2
    async def get_day(self, update, context):
        if update.message.text not in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
            kbrd = await self.days_buttons()
            await update.message.reply_text('Выберите день недели для расписания',
                                            reply_markup=kbrd)
            return self.step_date
        context.user_data['INFO']['Day'] = update.message.text
        if context.user_data['INFO']['Class'] == 'Учитель':
            await  self.get_teach.diff_teacher_timetable(update, context, context.user_data['INFO']['Day'],
                                                         context.user_data['INFO']['Name'],
                                                         context.user_data['INFO']['Familia'])
        else:
            await self.get_tt.get_timetable(update, context,
                                            context.user_data['INFO']['Day'],
                                            context.user_data['INFO']['Class'],
                                            context.user_data['INFO']['Name'],
                                            context.user_data['INFO']['Familia'])
        await update.message.reply_text('Выберите день или закончите выбор командой: /end_check')
        return self.step_date

    async def end_checking(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Поиск ученика/учителя прерван. Начать сначала: /check',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
