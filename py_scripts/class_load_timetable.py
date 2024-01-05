from telegram.ext import ConversationHandler
from py_scripts.funcs_back import *
from timetables_csv import *
from py_scripts.funcs_teachers import *


class LoadTimetables:
    step_pswrd = 1
    step_class = 2
    step_file = 3
    classes = ['6-9'] + [f'{i}{j}' for i in range(10, 12) for j in 'АБВГД'] + ['Учителя']

    async def classes_buttons(self):
        arr = [['6-9']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(10, 12)] + [['Учителя']]
        kbd = ReplyKeyboardMarkup(arr, resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        user = db_sess.query(User).filter(User.telegram_id == update.message.chat.id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_load')
        if user and user.role == "admin":
            await update.message.reply_text(f'Выберите нужный класс\n⚠️Для 6-9 классов нужно выбрать "6-9", для '
                                        f'загрузки учительского расписания - "Учителя"',
                                            reply_markup=await self.classes_buttons())
            context.user_data['in_conversation'] = True
            return self.step_class
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if my_hash(update.message.text) != password_hash:
            await update.message.reply_text('Неверный пароль. Загрузка расписаний прервана. '
                                            'Начать сначала: /load')
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(f'Выберите нужный класс\n⚠️Для 6-9 классов нужно выбрать "6-9", для '
                                        f'загрузки учительского расписания - "Учителя"',
                                        reply_markup=await self.classes_buttons())
        return self.step_class

    async def get_class(self, update, context):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        context.user_data['filename'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update, context):
        file_info = await bot.get_file(update.message.document.file_id)
        #await write_all(bot, prepare_for_markdown('❕') + '_*Бот будет недоступен в течение 1-2 минут\.*_\n' +
        #                prepare_for_markdown(f"Производится загрузка нового расписания для {context.user_data['filename']} класса."),
        #                parse_mode='MarkdownV2')
        if context.user_data['filename'] == 'Учителя':
            context.user_data['filename'] = 'teachers'
        await file_info.download_to_drive(path_to_timetables +
                                          f"{context.user_data['filename']}.pdf")
        if context.user_data['filename'] == '6-9':
            await extract_timetable_for_students_6_9()
        elif context.user_data['filename'] == 'teachers':
            await extract_timetable_for_teachers()
            context.user_data['FILE_UPLOADED2'] = True
        else:
            await extract_timetable_for_students_10_11([context.user_data['filename']])
        await update.message.reply_text('Файл загружен. Завершить: /end_load')
        context.user_data['FILE_UPLOADED'] = True
        await update.message.reply_text(f'Выберите нужный класс\n⚠️Для 6-9 классов нужно выбрать "6-9", для '
                                        f'загрузки учительского расписания - "Учителя"',
                                        reply_markup=await self.classes_buttons())
        return self.step_class

    async def end_setting(self, update, context):
        fl1 = 0
        if context.user_data.get('FILE_UPLOADED2'):
            await write_admins(bot, prepare_for_markdown('❗️') + '_*Уважаемые учителя\!*_' +
                            prepare_for_markdown(
                                '\nОбновлены ваши расписания. Они уже доступны к просмотру.'),
                            parse_mode='MarkdownV2')
            await update.message.reply_text(
                'Загрузка расписаний завершена. Проведена рассылка всем админам об обновлении расписаний. Начать сначала: /load',
                reply_markup=await timetable_kbrd())
            fl1 += 1
        if context.user_data.get('FILE_UPLOADED'):
            await write_all(bot, prepare_for_markdown('❗️') + '_*Уважаемые лицеисты\!*_' +
                            prepare_for_markdown('\nОбновлены расписания. Пожалуйста, проверьте ваше расписание!'),
                            parse_mode='MarkdownV2', all_=True)
            await update.message.reply_text(
                'Загрузка расписаний завершена. Проведена рассылка всем ученикам об обновлении расписаний. Начать сначала: /load',
                reply_markup=await timetable_kbrd())
            fl1 += 1
        if fl1 == 0:
            await update.message.reply_text('Загрузка расписаний завершена. Начать сначала: /load', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['FILE_UPLOADED'] = False
        context.user_data['FILE_UPLOADED2'] = False
        return ConversationHandler.END


class LoadEditsTT:
    step_pswrd = 1
    step_date = 2
    step_file = 3

    async def dates_buttons(self):
        day1 = datetime.now()
        if day1.weekday() == 6:
            day1 = day1 + timedelta(days=1)
            day2 = day1
        elif day1.weekday() == 5:
            day2 = day1 + timedelta(days=2)
        else:
            day2 = day1 + timedelta(days=1)
        day_1 = day1.isoformat().split('T')[0].split('-')
        day_2 = day2.isoformat().split('T')[0].split('-')
        day1 = f"{day_1[2]}.{day_1[1]}.{day_1[0]}"
        day2 = f"{day_2[2]}.{day_2[1]}.{day_2[0]}"
        if day1 == day2:
            arr = [[day1]]
        else:
            arr = [[day1], [day2]]
        kbd = ReplyKeyboardMarkup(arr, resize_keyboard=True)
        return kbd

    async def get_edits(self, next_day):
        t = ""
        edits_in_tt, for_which_day = await get_edits_in_timetable(next_day)
        if ('завтра' in for_which_day and next_day or 'сегодня' in for_which_day and not next_day):
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
                            class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                            res.append([f"{class__}, ", number_of_lesson,
                                        df.iloc[j]['Замены кабинетов'],
                                        df.iloc[j]['Урок по расписанию']])  # Изменения кабинетов, длина 4
                    sorted_res = sorted(res, key=lambda x: x[1])
                    text = '_' + prepare_for_markdown(df.columns.values[-1]) + '_\n\n'
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

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        user = db_sess.query(User).filter(User.telegram_id == update.message.chat.id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_changes')
        if user and user.role == 'admin':
            await update.message.reply_text(f'Выберите дату изменений в расписании или напишите свою (формат: ДД.ММ.ГГГГ):',
                                            reply_markup=await self.dates_buttons())
            context.user_data['in_conversation'] = True
            return self.step_date
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if my_hash(update.message.text) != password_hash:
            await update.message.reply_text('Неверный пароль. Загрузка изменений прервана. '
                                            'Начать сначала: /changes',
                                            reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(
            f'Выберите дату изменений в расписании или напишите свою (формат: ДД.ММ.ГГГГ):',
            reply_markup=await self.dates_buttons())
        return self.step_date

    async def get_date(self, update, context):
        if len(update.message.text.split('.')) != 3 or not all([i.isdigit() for i in update.message.text.split('.')]):
            await update.message.reply_text(f'Указана неверная дата "{update.message.text}"')
            return self.step_date
        context.user_data['changes_date'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update, context):
        file_info = await bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(path_to_changes + f"{context.user_data['changes_date']}.pdf")
        await save_edits_in_timetable_csv(context.user_data['changes_date'])
        next_day = not datetime.now().day == int(context.user_data["changes_date"].split('.')[0])
        await write_all(bot, prepare_for_markdown('❗️') + '_*Уважаемые лицеисты\!*_' +
                        prepare_for_markdown(
                            f'\nВ боте появились изменения на {context.user_data["changes_date"]}. '
                            f'Пожалуйста, проверьте ваше расписание на эту дату.\n\n') + await self.get_edits(next_day),
                        parse_mode='MarkdownV2', all_=True)
        await update.message.reply_text('Файл загружен. Проведена рассылка всем ученикам об обновлении расписаний. Начать сначала: /changes',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка изменений прервана',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
