import asyncio
from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.security import check_hash
from sqlalchemy_scripts.users import User
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
        await update.message.reply_text('Прервать загрузку кружков: /end_extra_load')
        if user and user.role == "admin":
            db_sess.close()
            await update.message.reply_text('Загрузите файл .xlsx')
            return self.step_file
        db_sess.close()
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Загрузка расписаний прервана\. '
                                            'Начать сначала\: \/extra\_load*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Загрузите файл .xlsx')
        return self.step_file

    async def load_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file_info = await context.bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(f"data/extra.xlsx")
        msg_ = await update.message.reply_text('⏳ *Идет формирование кружков в боте\. '
                                               'Время ожидания \- до 1 минуты*', parse_mode='MarkdownV2')
        try:
            await asyncio.gather(extract_extra_lessons_from_new_table())
            await context.bot.delete_message(update.message.chat_id, msg_.id)
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(f'⚠️ *При попытке сформировать кружки произошла '
                                            f'ошибка\: {prepare_for_markdown(e.__str__())}\. Проверьте формат файла*',
                                            parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END

        await update.message.reply_text(f'Загрузка кружков завершена.\nНачать сначала: /extra_load',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data["DIALOG_CMD"] = None
        context.user_data['in_conversation'] = False

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('⚠️ *Загрузка кружков прервана\. Начать сначала\: \/extra\_load*',
                                        parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
