from telegram.ext import ConversationHandler
from py_scripts.funcs_teachers import *


class LoadTimetables:
    step_pswrd = 1
    step_class = 2
    step_file = 3
    classes = ['6-9', '10-11', 'Учителя']

    async def classes_buttons(self):
        arr = [['6-9', '10-11']] + [['Учителя']]
        kbd = ReplyKeyboardMarkup(arr, resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_load')
        if user and user.role == "admin":
            await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
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
        await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
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
        if context.user_data['filename'] == 'Учителя':
            context.user_data['filename'] = 'teachers'
        await file_info.download_to_drive(path_to_timetables +
                                          f"{context.user_data['filename']}.pdf")
        msg_ = await update.message.reply_text('⏳ *Идет формирование расписаний в боте\, время ожидания \- 10\-20 секунд\.\.\.*', parse_mode='MarkdownV2')
        try:
            if context.user_data['filename'] == '6-9':
                await extract_timetable_for_students_6_9()
                context.user_data['FILE_UPLOADED'] = True
            elif context.user_data['filename'] == 'teachers':
                await extract_timetable_for_teachers()
                context.user_data['FILE_UPLOADED2'] = True
            else:
                await extract_timetable_for_students_10_11()
                context.user_data['FILE_UPLOADED'] = True
            await bot.delete_message(update.message.chat.id, msg_.id)
            await update.message.reply_text('Файл загружен. Завершить: /end_load')
        except Exception as e:
            await bot.delete_message(update.message.chat.id, msg_.id)
            await update.message.reply_text(f'При попытке сформировать расписание произошла ошибка: {e}. Проверьте формат файла.')
        await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
        return self.step_class

    async def end_setting(self, update, context):
        res1 = ''
        res2 = ''
        if context.user_data.get('FILE_UPLOADED2'):
            res1 = await write_admins(bot, prepare_for_markdown('❗️') + '_*Уважаемые учителя\!*_' +
                                     prepare_for_markdown(
                                         '\nОбновлены расписания пед. состава. Они уже доступны к просмотру.'),
                                     parse_mode='MarkdownV2')
        if context.user_data.get('FILE_UPLOADED'):
            res2 = await write_all(bot, prepare_for_markdown('❗️') + '_*Уважаемые лицеисты\!*_' +
                                  prepare_for_markdown(
                                      '\nОбновлены расписания. Пожалуйста, проверьте ваше расписание!'),
                                  parse_mode='MarkdownV2')
        if context.user_data.get('FILE_UPLOADED2'):
            await update.message.reply_text(
                f'Учителя получили уведомление о новых расписаниях.\n{res1}',
                reply_markup=await timetable_kbrd())
        if context.user_data.get('FILE_UPLOADED'):
            await update.message.reply_text(
                f'Ученики получили уведомление о новых расписаниях.\n{res2}',
                reply_markup=await timetable_kbrd())
        await update.message.reply_text('Загрузка расписаний завершена. Начать сначала: /load',
                                        reply_markup=await timetable_kbrd())
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
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
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
        try:
            tmp = update.message.text.split('.')
            date__ = datetime(year=int(tmp[2]), month=int(tmp[1]), day=int(tmp[0]))
            # Проверка корректности даты
        except Exception as e:
            await update.message.reply_text(f'Указана неверная дата "{update.message.text}". Ошибка: {e}')
            return self.step_date
        context.user_data['changes_date'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update, context):
        file_info = await bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(
            path_to_changes + f"{context.user_data['changes_date']}.pdf")
        msg_ = await update.message.reply_text(
            '⏳ *Идет формирование изменений в боте\, время ожидания \- 5\-10 секунд\.\.\.*',
            parse_mode='MarkdownV2')
        try:
            await save_edits_in_timetable_csv(context.user_data['changes_date'])
        except Exception as e:
            await bot.delete_message(update.message.chat.id, msg_.id)
            await update.message.reply_text(
                f'При попытке сохранить файл с изменениями произошла ошибка: {e}. Проверьте формат таблицы. Начать сначала: /changes',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        next_day = not datetime.now().day == int(context.user_data["changes_date"].split('.')[0])
        try:
            edits_text = await self.get_edits(next_day)
        except Exception as e:
            await bot.delete_message(update.message.chat.id, msg_.id)
            await update.message.reply_text(
                f'При попытке сформировать изменения произошла ошибка: {e}. Проверьте формат таблицы. Начать сначала: /changes',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END

        bot.delete_message(update.message.chat.id, msg_.id)
        res = await write_all(bot, prepare_for_markdown('❗️') + '_*Уважаемые лицеисты\!*_' +
                              prepare_for_markdown(
                                  f'\nВ боте появились изменения на {context.user_data["changes_date"]}. '
                                  f'Пожалуйста, проверьте ваше расписание на эту дату.\n\n') + edits_text,
                              parse_mode='MarkdownV2', all_=True)
        await update.message.reply_text(
            f'Файл загружен. Проведена рассылка всем ученикам об обновлении расписаний.\n{res}\nНачать сначала: /changes',
            reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка изменений прервана',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
