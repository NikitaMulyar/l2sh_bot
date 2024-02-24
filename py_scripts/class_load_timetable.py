import asyncio
from datetime import timedelta

import pandas as pd
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes
from py_scripts.consts import path_to_changes, path_to_timetables, COMMANDS
from py_scripts.funcs_back import get_edits_in_timetable, save_edits_in_timetable_csv, \
    prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.funcs_teachers import extract_timetable_for_teachers, get_edits_for_teacher
from py_scripts.security import check_hash
from py_scripts.timetables_csv import extract_timetable_for_students_6_9, extract_timetable_for_students_10_11
from sqlalchemy_scripts.users import User
from datetime import datetime
from py_scripts.funcs_students import get_edits_for_student
from sqlalchemy_scripts import db_session


async def write_about_new_timetable(context: ContextTypes.DEFAULT_TYPE):
    text = '❗️_*Уважаемые учителя и лицеисты\!*_\nВ бота загружены новые расписания\. Пожалуйста\, ознакомьтесь с ними'
    didnt_send = {}

    async def send_notif(user):
        try:
            await context.bot.send_message(user.chat_id, text, parse_mode='MarkdownV2')
        except Exception as e:
            if e.__str__() not in didnt_send:
                didnt_send[e.__str__()] = 1
            else:
                didnt_send[e.__str__()] += 1

    with open('list_new_timetable.txt', mode='r', encoding='utf-8') as f:
        arr_to_write = set(f.read().split('\n'))
    f.close()
    db_sess = db_session.create_session()
    all_users = db_sess.query(User).all()
    db_sess.close()
    users_to_send = []
    for user in all_users:
        var1 = f'{user.grade}'
        var2 = f'{user.surname} {user.name} {user.grade}'
        var3 = f'{user.surname} {user.name[0]}'
        if var1 in arr_to_write or var2 in arr_to_write or var3 in arr_to_write:
            users_to_send.append(user)

    tasks = [send_notif(user) for user in users_to_send]
    await asyncio.gather(*tasks)

    t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
    if t:
        t = '❗️ Сообщение не было отправлено некоторым пользователям по следующим причинам:\n' + t
    return t


async def write_about_edits(context: ContextTypes.DEFAULT_TYPE, text):
    didnt_send = {}

    async def send_notif(user: User):
        if user.role == 'student':
            edits_text = await get_edits_for_student(user.grade, context.user_data["changes_date"])
        else:
            edits_text = await get_edits_for_teacher(user.surname, user.name, context.user_data["changes_date"])
        if edits_text:
            total_len = len(text)
            ind = 0
            while ind < len(edits_text) and total_len + len(edits_text[ind]) < 4000:
                total_len += len(edits_text[ind])
                ind += 1
            frst = "".join(edits_text[:ind])
            scnd = "".join(edits_text[ind:])
        try:
            if edits_text:
                await context.bot.send_message(user.chat_id, "".join([text, frst]), parse_mode='MarkdownV2')
                if scnd:
                    await context.bot.send_message(user.chat_id, scnd, parse_mode='MarkdownV2')
        except Exception as e:
            if e.__str__() not in didnt_send:
                didnt_send[e.__str__()] = 1
            else:
                didnt_send[e.__str__()] += 1

    db_sess = db_session.create_session()
    all_users = db_sess.query(User).all()
    db_sess.close()

    tasks = [send_notif(user) for user in all_users]
    await asyncio.gather(*tasks)

    t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
    if t:
        t = '❗️ Сообщение не было отправлено некоторым пользователям по следующим причинам:\n' + t
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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['load']])
        context.user_data['in_conversation'] = True
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        db_sess.close()
        await update.message.reply_text('Прервать загрузку расписаний: /end_load')
        if user and user.role == "admin":
            await update.message.reply_text('Выберите нужный класс', reply_markup=await self.classes_buttons())
            with open('list_new_timetable.txt', mode='w', encoding='utf-8') as f:
                f.write('')
            f.close()
            return self.step_class
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Загрузка расписаний прервана\. '
                                            'Начать сначала\: \/load*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Выберите нужный класс', reply_markup=await self.classes_buttons())
        with open('list_new_timetable.txt', mode='w', encoding='utf-8') as f:
            f.write('')
        f.close()
        return self.step_class

    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'⚠️ *Указан неверный класс \"{prepare_for_markdown(update.message.text)}\"*',
                                            parse_mode='MarkdownV2')
            return self.step_class
        context.user_data['filename'] = update.message.text
        await update.message.reply_text('Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file_info = await context.bot.get_file(update.message.document.file_id)
        if context.user_data['filename'] == 'Учителя':
            context.user_data['filename'] = 'teachers'
        await file_info.download_to_drive(f"{path_to_timetables}{context.user_data['filename']}.pdf")
        msg_ = await update.message.reply_text('⏳ *Идет формирование расписаний в боте\. '
                                               'Время ожидания \- до 1 минуты*', parse_mode='MarkdownV2')
        try:
            if context.user_data['filename'] == '6-9':
                await asyncio.gather(extract_timetable_for_students_6_9())
                context.user_data['FILE_UPLOADED'] = True
            elif context.user_data['filename'] == 'teachers':
                await asyncio.gather(extract_timetable_for_teachers())
                context.user_data['FILE_UPLOADED2'] = True
            else:
                await asyncio.gather(extract_timetable_for_students_10_11())
                context.user_data['FILE_UPLOADED'] = True
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text('Файл загружен. Завершить: /end_load')
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(f'⚠️ *При попытке сформировать расписание произошла '
                                            f'ошибка\: {prepare_for_markdown(e)}\. Проверьте формат файла*',
                                            parse_mode='MarkdownV2')
        await update.message.reply_text(f'Выберите нужный класс', reply_markup=await self.classes_buttons())
        return self.step_class

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text('⏳ *Бот уведомляет пользователей о новом расписании\. Время ожидания \- до 1 минуты*',
                                              parse_mode='MarkdownV2')
        res = await write_about_new_timetable(context)
        if context.user_data.get('FILE_UPLOADED2'):
            await update.message.reply_text('Учителя получили уведомление о новых расписаниях',
                reply_markup=await timetable_kbrd())
        if context.user_data.get('FILE_UPLOADED'):
            await update.message.reply_text('Ученики получили уведомление о новых расписаниях',
                reply_markup=await timetable_kbrd())
        await msg.delete()
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

    async def create_list_of_edits_lessons(self, df: pd.DataFrame):
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
                                    f'{cabinet} каб.',
                                    "".join([df.iloc[j]['Урок по расписанию'], ' каб.'])])  # Кабинет не указан, длина 5
                    else:
                        res.append([f"{class__}, ", number_of_lesson,
                                    f'{subject}, {cabinet} каб.', teacher,
                                    "".join([df.iloc[j]['Урок по расписанию'], ' каб.'])])  # Все указано, длина 5
                else:
                    tmp = " ".join(df.iloc[j]['Урок по расписанию'].split('\n'))
                    res.append([f"{class__}, ", number_of_lesson,
                                f"{subject}\n(Урок по расписанию: {tmp} каб.)"])  # Отмена урока, длина 3
            else:
                class__ = " ".join(df.iloc[j]['Класс'].split('\n'))
                res.append([f"{class__}, ", number_of_lesson,
                            df.iloc[j]['Замены кабинетов'],
                            "".join([df.iloc[j]['Урок по расписанию'], ' каб.'])])  # Изменения кабинетов, длина 4
        return sorted(res, key=lambda x: x[1])

    async def get_edits(self, date):
        result0 = []
        edits_in_tt, for_which_day = await get_edits_in_timetable(date)
        if len(edits_in_tt) != 0:
            for df in edits_in_tt:
                sorted_res = await self.create_list_of_edits_lessons(df)
                result = [f'_{prepare_for_markdown(df.columns.values[-1])}_\n\n']
                for line in sorted_res:
                    urok_po_rasp = " ".join(line[-1].split("\n"))
                    if len(line) == 3:
                        curr = prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]}\n\n')
                    elif len(line) == 4:  # Замены каб.
                        if line[2] == urok_po_rasp == '':
                            curr = prepare_for_markdown(f'{line[0]}{line[1]}\n\n')
                        else:
                            curr = prepare_for_markdown(
                                f'{line[0]}{line[1]} урок(и): {line[2]}\n(Урок по расписанию: '
                                f'{urok_po_rasp})\n\n')
                    else:
                        curr = prepare_for_markdown(
                            f'{line[0]}{line[1]} урок(и): {line[2]} (учитель: {line[3]})'
                            f'\n(Урок по расписанию: {urok_po_rasp})\n\n')
                    result.append(curr.replace('ё', 'е'))
                result0.append(for_which_day)
                result0.extend(result)
        return result0

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['changes']])
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        db_sess.close()
        await update.message.reply_text('Прервать загрузку изменений: /end_changes')
        if user and user.role == 'admin':
            await update.message.reply_text('Выберите дату изменений в расписании или напишите свою (формат: ДД.ММ.ГГГГ):',
                                            reply_markup=await self.dates_buttons())
            return self.step_date
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Загрузка изменений прервана\. '
                                            'Начать сначала\: \/changes*', parse_mode='MarkdownV2',
                                            reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Выберите дату изменений в расписании (формат: ДД.ММ.ГГГГ):',
                                        reply_markup=await self.dates_buttons())
        return self.step_date

    async def get_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            tmp = update.message.text.split('.')
            date__ = datetime(year=int(tmp[2]), month=int(tmp[1]), day=int(tmp[0]))
            # Проверка корректности даты
        except Exception as e:
            await update.message.reply_text(f'⚠️ *Указана неверная дата '
                                            f'\"{prepare_for_markdown(update.message.text)}\"\. '
                                            f'Ошибка\: {prepare_for_markdown(e)}*',
                                            parse_mode='MarkdownV2')
            return self.step_date
        context.user_data['changes_date'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file_info = await context.bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(
            path_to_changes + f"{context.user_data['changes_date']}.pdf")
        msg_ = await update.message.reply_text('⏳ *Идет формирование изменений в боте\. '
                                               'Время ожидания \- до 10 секунд*',
                                               parse_mode='MarkdownV2')
        try:
            await save_edits_in_timetable_csv(context.user_data['changes_date'])
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(f'⚠️ *При попытке сохранить файл с изменениями '
                                            f'произошла ошибка\: {prepare_for_markdown(e)}\. '
                                            f'Проверьте формат таблицы\. Начать сначала\: \/changes*',
                                            reply_markup=await timetable_kbrd(),
                                            parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        try:
            edits_text = await self.get_edits(context.user_data["changes_date"])
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(
                f'При попытке сформировать изменения произошла ошибка: {e}. Проверьте формат таблицы. Начать сначала: /changes',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await context.bot.delete_message(update.message.chat_id, msg_.id)
        msg = await update.message.reply_text(
            '⏳ *Бот уведомляет пользователей о новых изменениях\. Время ожидания \- до 1 минуты*',
            parse_mode='MarkdownV2')
        notif_text = (f'❗️_*Уважаемые учителя и лицеисты\!*_\nВ боте появились изменения на '
                      f'{prepare_for_markdown(context.user_data["changes_date"])}\. Пожалуйста\, '
                      f'проверьте ваше расписание на эту дату\n\n')
        res = await write_about_edits(context, notif_text)
        await context.bot.delete_message(msg.id)
        ind = 0
        prev_ = 0
        total_len = 0
        while ind < len(edits_text):
            while ind < len(edits_text) and total_len + len(edits_text[ind]) < 4000:
                total_len += len(edits_text[ind])
                ind += 1
            total_len = 0
            await update.message.reply_text(f'*Все изменения \(просмотр для Вас\)\:*\n\n{"".join(edits_text[prev_:ind])}', parse_mode='MarkdownV2')
            prev_ = ind
        await update.message.reply_text(
            f'Файл загружен. Проведена рассылка ученикам и учителям, у которых есть изменения.\n{res}\nНачать сначала: /changes',
            reply_markup=await timetable_kbrd())
        context.user_data['DIALOG_CMD'] = None
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Загрузка изменений прервана',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
