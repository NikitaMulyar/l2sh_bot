import asyncio
import os.path
from datetime import datetime

import telegram
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from py_scripts.security import check_hash
from sqlalchemy_scripts.events import Event
from sqlalchemy_scripts.users import User
from sqlalchemy_scripts import db_session


class EventsClass:
    step_title = 2
    step_theme = 3
    step_start_date = 4
    step_end_date = 5
    step_description = 6
    step_place = 7
    step_author = 8
    step_files = 9
    step_pswrd = 1

    async def ready_btn(self):
        kbd = ReplyKeyboardMarkup([['✅Готово']], resize_keyboard=True)
        return kbd

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            db_sess.close()
            await update.message.reply_text('⚠️ *Вы не заполнили свои данные\. Напишите \/start и заполните свои данные*',
                                            parse_mode='MarkdownV2')
            return ConversationHandler.END
        await update.message.reply_text('Прервать добавление события: /end_new_event')
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['new_event']])
        if user.role == 'admin':
            await update.message.reply_text('*Шаг 1 из 8\.* Введите название мероприятия\:',
                                            parse_mode='MarkdownV2')
            context.user_data['EVENT_INFO'] = dict()
            db_sess.close()
            return self.step_title
        db_sess.close()
        await update.message.reply_text('Введите пароль:')
        return self.step_pswrd

    async def get_psw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Настройка мероприятия прервана\. '
                                            'Начать сначала\: \/new\_event*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('*Шаг 1 из 8\.* Введите название мероприятия\:',
                                        parse_mode='MarkdownV2')
        context.user_data['EVENT_INFO'] = dict()
        return self.step_title

    async def get_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['EVENT_INFO']['title'] = update.message.text
        await update.message.reply_text('*Шаг 2 из 8\.* Введите тему мероприятия\:',
                                        parse_mode='MarkdownV2')
        return self.step_theme

    async def get_theme(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['EVENT_INFO']['theme'] = update.message.text
        await update.message.reply_text('*Шаг 3 из 8\.* Введите дату начала мероприятия '
                                        '\(формат строго ДД\.ММ\.ГГГГ\)\:',
                                        parse_mode='MarkdownV2')
        return self.step_start_date

    async def get_start_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        r = update.message.text.split('.')
        try:
            date__ = datetime(day=int(r[0]), month=int(r[1]), year=int(r[2]))
        except Exception:
            await update.message.reply_text('⚠️ *Неверная дата\. Попробуйте еще раз*',
                                            parse_mode='MarkdownV2')
            return self.step_start_date
        context.user_data['EVENT_INFO']['date_start'] = date__
        await update.message.reply_text('*Шаг 4 из 8\.* Введите дату окончания мероприятия '
                                        '\(она может совпадать с предыдущей датой\) '
                                        '\(формат строго ДД\.ММ\.ГГГГ\)\:',
                                        parse_mode='MarkdownV2')
        return self.step_end_date

    async def get_end_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        r = update.message.text.split('.')
        try:
            date__ = datetime(day=int(r[0]), month=int(r[1]), year=int(r[2]))
        except Exception:
            await update.message.reply_text('⚠️ *Неверная дата\. Попробуйте еще раз*',
                                            parse_mode='MarkdownV2')
            return self.step_end_date
        context.user_data['EVENT_INFO']['date_end'] = date__
        await update.message.reply_text('*Шаг 5 из 8\.* Напишите описание мероприятия\:',
                                        parse_mode='MarkdownV2')
        return self.step_description

    async def get_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['EVENT_INFO']['description'] = update.message.text
        await update.message.reply_text('*Шаг 6 из 8\.* Введите место проведения '
                                        '\(например\, Л2Ш\)\:',
                                        parse_mode='MarkdownV2')
        return self.step_place

    async def get_place(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['EVENT_INFO']['place'] = update.message.text
        await update.message.reply_text('*Шаг 7 из 8\.* Напишите\, кто организует данное мероприятие '
                                        '\(например\, Воспитательная служба Лицея\)\:',
                                        parse_mode='MarkdownV2')
        return self.step_author

    async def get_author(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['EVENT_INFO']['author'] = update.message.text
        await update.message.reply_text('*Шаг 8 из 8\.* По желанию\, прикрепите 1 документ весом не более 20МБ '
                                        '\(если вы не хотите прикреплять документ\, то нажмите на кнопку \"✅Готово\"\)',
                                        parse_mode='MarkdownV2', reply_markup=await self.ready_btn())
        return self.step_files

    async def get_btn_ready(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return self.get_file(update, context, no_file=True)

    async def get_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE, no_file=False):
        if not no_file:
            try:
                if update.message.audio is None:
                    file_info = await context.bot.get_file(update.message.document.file_id)
                    path_ = "".join(['event_files/', str(update.message.chat_id), '_',
                                     update.message.document.file_name])
                    await file_info.download_to_drive(path_)
                else:
                    file_info = await context.bot.get_file(update.message.audio.file_id)
                    path_ = "".join(['event_files/', str(update.message.chat_id), '_',
                                     update.message.audio.file_name])
                    await file_info.download_to_drive(path_)
            except Exception as e:
                await update.message.reply_text(f'⚠️ *Файл не загружен\, так как он весит более 20МБ или по причине\:* '
                                                f'{prepare_for_markdown(e.__str__())}\. Попробуйте загрузить еще раз',
                                                parse_mode='MarkdownV2')
                return self.step_files
            context.user_data['EVENT_INFO']['file_path'] = path_
        else:
            context.user_data['EVENT_INFO']['file_path'] = ''
        db_sess = db_session.create_session()
        event = Event(
            title=context.user_data['EVENT_INFO']['title'],
            theme=context.user_data['EVENT_INFO']['theme'],
            description=context.user_data['EVENT_INFO']['description'],
            date_start=context.user_data['EVENT_INFO']['date_start'],
            date_end=context.user_data['EVENT_INFO']['date_end'],
            place=context.user_data['EVENT_INFO']['place'],
            author=context.user_data['EVENT_INFO']['author'],
            status=0,
            file_path=context.user_data['EVENT_INFO']['file_path'],
            user_id=update.message.from_user.id
        )
        db_sess.add(event)
        db_sess.commit()
        db_sess.close()
        await update.message.reply_text('Мероприятие успешно добавлено! Настройка завершена, начать сначала: '
                                        '/new_event', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['EVENT_INFO'] = dict()
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['EVENT_INFO'] = dict()
        context.user_data['DIALOG_CMD'] = None

    async def end_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Настройка мероприятия прервана. Начать сначала: /new_event',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['EVENT_INFO'] = dict()
        return ConversationHandler.END
