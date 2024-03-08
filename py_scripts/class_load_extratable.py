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
from py_scripts.funcs_extra_lessons import extract_extra_lessons_from_new_table


class Load_Extra_Table:
    step_pswrd = 1
    step_file = 2

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['extra_load']])
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == update.message.chat_id).first()
        db_sess.close()
        await update.message.reply_text('Прервать загрузку расписаний: /end_extra_load')
        if user and user.role == "admin":
            return self.step_file
        await update.message.reply_text('Введите пароль администратора:')
        return self.step_pswrd

    async def get_pswrd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Загрузка расписаний прервана\. '
                                            'Начать сначала\: \/extra_load*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Загрузите файл .xlsx')
        return self.step_file

    async def load_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file_info = await context.bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(f"data/extra.xlsx")
        msg_ = await update.message.reply_text('⏳ *Идет формирование расписаний в боте\. '
                                               'Время ожидания \- до 1 минуты*', parse_mode='MarkdownV2')
        try:
            await asyncio.gather(extract_extra_lessons_from_new_table())
            # await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text('Файл успешно загружен')
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(f'⚠️ *При попытке сформировать расписание произошла '
                                            f'ошибка\: {prepare_for_markdown(e.__str__())}\. Проверьте формат файла*',
                                            parse_mode='MarkdownV2')

        await update.message.reply_text(f'Загрузка расписаний завершена.\nНачать сначала: /extra_load',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('⚠️ *Загрузка расписаний прервана\. Начать сначала\: \/end_extra_load*',
                                        parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        context.user_data['FILE_UPLOADED'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
