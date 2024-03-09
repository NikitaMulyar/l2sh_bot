import asyncio

import telegram
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.consts import COMMANDS
from telegram.ext import ConversationHandler, ContextTypes
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from py_scripts.security import check_hash
from sqlalchemy_scripts.users import User
from sqlalchemy_scripts import db_session


async def make_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE, step_text):
    didnt_send = {}
    arr = []
    for file in context.user_data['ATTACHMENTS']:
        arr.append(telegram.InputMediaDocument(media=file))

    async def send_msg(user: User):
        try:
            if len(arr) >= 2:
                msg = await context.bot.send_media_group(user.chat_id, arr, caption=mail_text,
                                                         parse_mode='MarkdownV2')
                msg = msg[0]
            elif len(arr) == 1:
                msg = await context.bot.send_document(user.chat_id, arr[0].media, caption=mail_text,
                                                      parse_mode='MarkdownV2')
            else:
                msg = await context.bot.send_message(user.chat_id, mail_text, parse_mode='MarkdownV2')
            await msg.pin()
        except Exception as e:
            if e.__str__() not in didnt_send:
                didnt_send[e.__str__()] = 1
            else:
                didnt_send[e.__str__()] += 1

    msg__ = await update.message.reply_text(f'⏳ *Запущен процесс рассылки\. Время ожидания \- до 1 минуты*',
                                            parse_mode='MarkdownV2')
    chat_id = update.message.chat_id
    db_sess = db_session.create_session()
    author = db_sess.query(User).filter(User.chat_id == chat_id).first()
    if context.user_data['PARAL'] == 'Всем':
        all_users = db_sess.query(User).all()
    elif context.user_data['PARAL'] == 'Админы':
        all_users = db_sess.query(User).filter(User.role == 'admin').all()
    elif context.user_data['PARAL'] == 'Учителя':
        all_users = db_sess.query(User).filter((User.role == 'teacher') | (User.role == 'admin')).all()
    elif context.user_data['PARAL'] == 'Учащиеся':
        all_users = db_sess.query(User).filter((User.role == 'student') | (User.role == 'admin')).all()
    else:
        if context.user_data['CLASS'] == 'Всем':
            all_users = db_sess.query(User).filter((User.number == context.user_data['PARAL']) |
                                                   (User.role == 'admin')).all()
        else:
            all_users = db_sess.query(User).filter((User.number == context.user_data['CLASS']) |
                                                   (User.role == 'admin')).all()
    db_sess.close()
    if author.grade is None and author.role == 'teacher':
        user_grade = 'Учитель'
    elif author.grade is None and author.role == 'admin':
        user_grade = 'Админ'
    else:
        user_grade = author.grade
    mail_text = "\n\n".join((['📬*Новое сообщение\!*📬',
                          context.user_data['MESSAGE'],
                          prepare_for_markdown(f'От {author.surname} {author.name}, {user_grade}')]))

    tasks = [send_msg(user) for user in all_users]
    await asyncio.gather(*tasks)

    context.user_data['ATTACHMENTS'].clear()
    context.user_data['FILES_SIZE'] = 0
    p, c = context.user_data['PARAL'], context.user_data['CLASS']
    t = "\n".join([f'Тип ошибки "{k}": {v} человек' for k, v in didnt_send.items()])
    if t:
        t = "\n".join(['❗️Сообщение не было отправлено некоторым пользователям по следующим причинам:', t])
    try:
        text_ = "\n\n\n".join(['Сообщение\:', mail_text,
                           prepare_for_markdown(f'было отправлено в параллель "{p}", класс: "{c}"')])

        if len(arr) >= 2:
            await context.bot.send_media_group(update.message.chat_id, arr, caption=text_,
                                               parse_mode='MarkdownV2')
        elif len(arr) == 1:
            await context.bot.send_document(update.message.chat_id, arr[0].media, caption=text_,
                                            parse_mode='MarkdownV2')
        else:
            await context.bot.send_message(update.message.chat_id, text_, parse_mode='MarkdownV2')

        await update.message.reply_text(f'Настройка рассылки окончена.\n{t}\nНачать сначала: /mail',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        await msg__.delete()
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(
            f'⚠️ *Ошибка при форматировании текста \(ошибка\: {prepare_for_markdown(e.__str__())}\)\. Попробуйте исправить текст и '
            f'отправьте его заново\. ❗️НЕЛЬЗЯ использовать нижнее подчеркивание и зачеркивание\!*',
            parse_mode='MarkdownV2')
        await msg__.delete()
        return step_text


class MailTo:
    parallels = ['6', '7', '8', '9', '10', '11']
    classes = {f'{i}': [f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)}
    classes['6'] = ['6А', '6Б', '6В']
    step_pswrd = 1
    step_parallel = 2
    step_class = 3
    step_text = 4
    step_attachments = 5
    size_limit = 100

    async def mailing_parallels_kbrd(self):
        btns = []
        for i in self.parallels:
            btns.append(KeyboardButton(i))

        kbd = ReplyKeyboardMarkup(
            [btns, [KeyboardButton('Админы'), KeyboardButton('Учителя')], [KeyboardButton('Учащиеся')], [KeyboardButton('Всем')]],
            resize_keyboard=True)
        return kbd

    async def mailing_classes_kbrd(self, parallel):
        btns = []
        for i in self.classes[parallel]:
            btns.append(KeyboardButton(i))
        kbd = ReplyKeyboardMarkup([btns, [KeyboardButton(f'Всем')]],
                                  resize_keyboard=True)
        return kbd

    async def attachments_kbrd(self):
        kbd = ReplyKeyboardMarkup([['📧Готово📧']],
                                  resize_keyboard=True)
        return kbd

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        db_sess.close()
        if not user:
            await update.message.reply_text('⚠️ *Вы не заполнили свои данные\. Напишите \/start и заполните свои данные*',
                                            parse_mode='MarkdownV2')
            return ConversationHandler.END
        await update.message.reply_text('Прервать настройку рассылки: /end_mail')
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['mail']])
        if user.role == 'admin':
            text_to_send = (f'*Рассылка осуществляется под аккаунтом\: {prepare_for_markdown(user.surname)} '
                            f'{prepare_for_markdown(user.name)}\, Админ*\nВыберите параллель\, к которой будет обращена рассылка\:')
            await update.message.reply_text(text_to_send, reply_markup=await self.mailing_parallels_kbrd(),
                                            parse_mode='MarkdownV2')
            return self.step_parallel
        await update.message.reply_text('Введите пароль:')
        return self.step_pswrd

    async def get_psw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Настройка рассылки прервана\. '
                                            'Начать сначала\: \/mail*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        db_sess.close()
        grade = user.grade
        if grade is None:
            grade = 'Учитель'
        text_to_send = (f'*Рассылка осуществляется под аккаунтом\: {prepare_for_markdown(user.surname)} '
                        f'{prepare_for_markdown(user.name)}\, {prepare_for_markdown(grade)}*\nВыберите параллель\, к которой будет обращена рассылка\:')
        await update.message.reply_text(text_to_send, reply_markup=await self.mailing_parallels_kbrd(),
                                        parse_mode='MarkdownV2')
        return self.step_parallel

    async def get_parallel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text in ['Всем', 'Админы', 'Учителя', 'Учащиеся']:
            context.user_data['PARAL'] = update.message.text
            context.user_data['CLASS'] = update.message.text
            await update.message.reply_text('Напишите сообщение для рассылки:',
                                            reply_markup=ReplyKeyboardRemove())
            return self.step_text
        if update.message.text not in self.parallels:
            await update.message.reply_text('Выберите параллель, к которой будет обращена рассылка:',
                                            reply_markup=await self.mailing_parallels_kbrd())
            return self.step_parallel
        context.user_data['PARAL'] = update.message.text
        await update.message.reply_text('Выберите класс, к которому будет обращена рассылка:',
                                        reply_markup=await self.mailing_classes_kbrd(
                                            context.user_data['PARAL']))
        return self.step_class

    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == 'Всем':
            context.user_data['CLASS'] = update.message.text
            await update.message.reply_text('Напишите сообщение для рассылки:',
                                            reply_markup=ReplyKeyboardRemove())
            return self.step_text
        classes = self.classes[context.user_data['PARAL']]
        if update.message.text not in classes:
            await update.message.reply_text(
                'Выберите класс, к которому будет обращена рассылка:',
                reply_markup=await self.mailing_classes_kbrd(context.user_data['PARAL']))
            return self.step_class
        context.user_data['CLASS'] = update.message.text
        await update.message.reply_text('Напишите сообщение для рассылки\n❗️НЕЛЬЗЯ использовать нижнее подчеркивание и зачеркивание!',
                                        reply_markup=ReplyKeyboardRemove())
        return self.step_text

    async def get_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['MESSAGE'] = update.message.text_markdown_v2
        text_ = 'Прикрепите вложения по желанию\.\n⚠️ *Инструкция по прикреплению файлов*\n'
        text_2 = prepare_for_markdown(f'1. Суммарный размер файлов не может превышать {self.size_limit}МБ. '
                                     'Размер каждого файла не должен превышать 20МБ.\n'
                                     '2. Можно прикрепить не более 10 файлов (если будет отправлено более '
                                     '10 файлов, бот отправит только первые 10).\n'
                                     '3. При прикреплении тяжелых файлов (которые достигают лимит), '
                                     'рассылка может замедлиться.\n'
                                     '4. ⚠️ Если вы захотите завершить прикрепление файлов, нажмите на кнопку "Готово"')
        text_ = "".join([text_, text_2])
        await update.message.reply_text(text_, reply_markup=await self.attachments_kbrd(),
                                        parse_mode='MarkdownV2')
        await context.bot.send_photo(update.message.chat_id, 'data/instruction.jpg')
        context.user_data['ATTACHMENTS'] = []
        context.user_data['FILES_SIZE'] = 0
        return self.step_attachments

    async def get_attachments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if update.message.audio is None:
                file_info = await context.bot.get_file(update.message.document.file_id)
                file_id = update.message.document.file_id
            else:
                file_info = await context.bot.get_file(update.message.audio.file_id)
                file_id = update.message.audio.file_id
            if file_info.file_size / 1024 / 1024 > 50:
                raise Exception
        except Exception as e:
            await update.message.reply_text(f'⚠️ *Файл не загружен\, так как он весит более 50МБ или не '
                                            f'умещается в суммарный лимит {self.size_limit}МБ\.* '
                                            f'Загрузка файлов продолжается\. '
                                            f'Если вы хотите завершить прикрепление файлов\, '
                                            f'нажмите на кнопку \"Готово\"',
                                            parse_mode='MarkdownV2')
            return self.step_attachments
        context.user_data['FILES_SIZE'] += file_info.file_size
        context.user_data['ATTACHMENTS'].append(file_id)
        if context.user_data['FILES_SIZE'] / 1024 / 1024 > self.size_limit:
            context.user_data['ATTACHMENTS'] = context.user_data['ATTACHMENTS'][:-1]
            context.user_data['FILES_SIZE'] -= file_info.file_size
            await update.message.reply_text('⚠️ *Файл не может быть отправлен из\-за лимита суммарного '
                                            'размера файлов\.* Загрузка файлов продолжается\. '
                                            'Если вы хотите завершить прикрепление файлов\, '
                                            'нажмите на кнопку \"Готово\"',
                                            parse_mode='MarkdownV2')
            return self.step_attachments
        if len(context.user_data['ATTACHMENTS']) == 10:
            await update.message.reply_text('⚠️ *Достигнут лимит по количеству файлов\. '
                                            'Будут отправлены только первые 10\.*',
                                            parse_mode='MarkdownV2')
            return await self.send_message(update, context)
        await update.message.reply_text('Загрузка файлов продолжается. '
                                        'Если вы хотите завершить прикрепление файлов, '
                                        'нажмите на кнопку "Готово"')
        return self.step_attachments

    async def get_ready(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == '📧Готово📧':
            return await self.send_message(update, context)
        return self.step_attachments

    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await make_mailing(update, context, self.step_text)

    async def end_mailing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Настройка рассылки прервана. Начать сначала: /mail',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
