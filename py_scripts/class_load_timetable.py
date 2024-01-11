from datetime import timedelta
from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from py_scripts.consts import path_to_changes, path_to_timetables, COMMANDS
from py_scripts.funcs_back import bot, get_edits_in_timetable, save_edits_in_timetable_csv, \
    db_sess, prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.funcs_teachers import extract_timetable_for_teachers, get_edits_for_teacher
from py_scripts.security import check_hash
from py_scripts.timetables_csv import extract_timetable_for_students_6_9, extract_timetable_for_students_10_11
from sqlalchemy_scripts.users import User
from datetime import datetime
from py_scripts.funcs_students import get_edits_for_student


async def write_about_new_timetable():
    all_users = db_sess.query(User).all()
    didnt_send = {}
    with open('list_new_timetable.txt', mode='r', encoding='utf-8') as f:
        arr_to_write = set(f.read().split('\n'))
    f.close()
    text12 = (prepare_for_markdown('❗️') + '_*Уважаемые лицеисты\!*_' +
              prepare_for_markdown('\nВ бота загружены новые расписания. '
                                   'Пожалуйста, ознакомьтесь с ними.'))
    text3 = (prepare_for_markdown('❗️') + '_*Уважаемые учителя\!*_' +
             prepare_for_markdown('\nОбновлены расписания пед. состава. Они будут доступны к '
                                  'просмотру через несколько минут.'))
    for user in all_users:
        try:
            var1 = f'{user.grade}'
            var2 = f'{user.surname} {user.name} {user.grade}'
            var3 = f'{user.surname} {user.name[0]}'
            if var1 in arr_to_write or var2 in arr_to_write:
                await bot.send_message(user.chat_id, text12, parse_mode='MarkdownV2')
            elif var3 in arr_to_write:
                await bot.send_message(user.chat_id, text3, parse_mode='MarkdownV2')
        except Exception as e:
            if e.__str__() not in didnt_send:
                didnt_send[e.__str__()] = 1
            else:
                didnt_send[e.__str__()] += 1
            continue
    t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
    if t:
        t = '❗️Сообщение не было отправлено некоторым пользователям по следующим причинам:\n' + t
    return t


async def write_about_edits(context, text):
    all_users = db_sess.query(User).all()
    didnt_send = {}
    for user in all_users:
        try:
            if user.role == 'student':
                edits_text = await get_edits_for_student(context, user.grade)
            else:
                edits_text = await get_edits_for_teacher(context, user.surname, user.name)
            if edits_text:
                await bot.send_message(user.chat_id, text + edits_text, parse_mode='MarkdownV2')
        except Exception as e:
            if e.__str__() not in didnt_send:
                didnt_send[e.__str__()] = 1
            else:
                didnt_send[e.__str__()] += 1
            continue
    t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
    if t:
        t = '❗️Сообщение не было отправлено некоторым пользователям по следующим причинам:\n' + t
    return t


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
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['load']
        context.user_data['in_conversation'] = True
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_load')
        if user and user.role == "admin":
            await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
            with open('list_new_timetable.txt', mode='w', encoding='utf-8') as f:
                f.write('')
            f.close()
            return self.step_class
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if not check_hash(update.message.text):
            await update.message.reply_text('Неверный пароль. Загрузка расписаний прервана. '
                                            'Начать сначала: /load')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
        with open('list_new_timetable.txt', mode='w', encoding='utf-8') as f:
            f.write('')
        f.close()
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
        res = await write_about_new_timetable()
        if context.user_data.get('FILE_UPLOADED2'):
            await update.message.reply_text(
                f'Учителя получили уведомление о новых расписаниях.',
                reply_markup=await timetable_kbrd())
        if context.user_data.get('FILE_UPLOADED'):
            await update.message.reply_text(
                f'Ученики получили уведомление о новых расписаниях.',
                reply_markup=await timetable_kbrd())
        await update.message.reply_text(f'Загрузка расписаний завершена.\n{res}\nНачать сначала: /load',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['FILE_UPLOADED'] = False
        context.user_data['FILE_UPLOADED2'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END


class LoadEditsTT:
    step_pswrd = 1
    step_date = 2
    step_file = 3

    """async def write_about_new_edits(self, context):
        all_users = db_sess.query(User).all()
        didnt_send = {}
        with open('list_new_edits.txt', mode='r', encoding='utf-8') as f:
            arr_to_write = f.read()
            f.close()
        text = (prepare_for_markdown('❗️') + '_*Уважаемые учителя и лицеисты\!*_' + 
                prepare_for_markdown(f'\nВ боте появились изменения на {context.user_data["changes_date"]}. '
                                     f'Пожалуйста, проверьте ваше расписание на эту дату.\n\n'))
        for user in all_users:
            try:
                var1 = f'{user.grade}'
                var2 = f'{user.surname} {user.name} {user.grade}'
                var3 = f'{user.surname} {user.name[0]}'
                if var1 in arr_to_write or var2 in arr_to_write or var3:
                    await bot.send_message(user.chat_id, text, parse_mode='MarkdownV2')
                elif var3 in arr_to_write:
                    await bot.send_message(user.chat_id, text3, parse_mode='MarkdownV2')
            except Exception as e:
                if e.__str__() not in didnt_send:
                    didnt_send[e.__str__()] = 1
                else:
                    didnt_send[e.__str__()] += 1
                continue
        t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
        if t:
            t = '❗️Сообщение не было отправлено некоторым пользователям по следующим причинам:\n' + t
        return t"""

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
                            #with open('list_new_edits.txt', mode='a', encoding='utf-8') as f:
                            #    f.write(f'{line[0]}\n')
                            #    f.close()
                        elif len(line) == 4:  # Замены каб.
                            if line[2] == urok_po_rasp == '':
                                text += prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                                #with open('list_new_edits.txt', mode='a', encoding='utf-8') as f:
                                #    f.write(f'{line[0]}\n{line[1]}\n')
                                #    f.close()
                            else:
                                text += prepare_for_markdown(
                                    f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                    f'{urok_po_rasp})\n\n')
                                #with open('list_new_edits.txt', mode='a', encoding='utf-8') as f:
                                #    f.write(f'{line[0]}\n{line[2]}\n{urok_po_rasp}\n')
                                #    f.close()
                        else:
                            text += prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                                f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                            #with open('list_new_edits.txt', mode='a', encoding='utf-8') as f:
                            #    f.write(f'{line[0]}\n{line[2]}\n{line[3]}\n{urok_po_rasp}\n')
                            #    f.close()
                    if flag:
                        t += for_which_day
                        t += text
        return t

    async def start(self, update, context):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['changes']
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_changes')
        if user and user.role == 'admin':
            await update.message.reply_text(f'Выберите дату изменений в расписании или напишите свою (формат: ДД.ММ.ГГГГ):',
                                            reply_markup=await self.dates_buttons())
            return self.step_date
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if not check_hash(update.message.text):
            await update.message.reply_text('Неверный пароль. Загрузка изменений прервана. '
                                            'Начать сначала: /changes',
                                            reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text(
            f'Выберите дату изменений в расписании (формат: ДД.ММ.ГГГГ):',
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
        #with open('list_new_edits.txt', mode='w', encoding='utf-8') as f:
        #    f.write('')
        #    f.close()
        now_ = datetime.now()
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
            context.user_data['DIALOG_CMD'] = None
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
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await bot.delete_message(update.message.chat.id, msg_.id)

        tmp = context.user_data["changes_date"].split('.')
        edits_date = (int(tmp[2]), int(tmp[1]), int(tmp[0]))
        today_date = (now_.year, now_.month, now_.day)
        context.user_data['NEXT_DAY_TT'] = not today_date == edits_date

        res = await write_about_edits(context,
                                      prepare_for_markdown('❗️') + '_*Уважаемые учителя и лицеисты\!*_' +
                                      prepare_for_markdown(
                                      f'\nВ боте появились изменения на {context.user_data["changes_date"]}. '
                                      f'Пожалуйста, проверьте ваше расписание на эту дату.\n\n'))
        await update.message.reply_text(
            f'Файл загружен. Проведена рассылка ученикам и учителям, у которых есть изменения.\n{res}\nНачать сначала: /changes',
            reply_markup=await timetable_kbrd())
        context.user_data['DIALOG_CMD'] = None
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка изменений прервана',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
