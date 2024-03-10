from py_scripts.funcs_back import throttle, check_busy, prepare_for_markdown
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from telegram import Update
from sqlalchemy_scripts.stickers_table import Sticker
from random import choice
from sqlalchemy_scripts.users import User
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from sqlalchemy_scripts import db_session


class GetSticker:
    step_upload = 1

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            db_sess.close()
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return ConversationHandler.END
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            db_sess.close()
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return ConversationHandler.END
        db_sess.close()
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['sticker']])
        await update.message.reply_text(f'Жду стикер! Закончить: /')
        return self.step_upload

    @throttle()
    async def get_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        sticker_id = update.message.sticker.file_id
        sticker_unique_id = update.message.sticker.file_unique_id
        db_sess = db_session.create_session()
        if not db_sess.query(Sticker).filter(Sticker.file_unique_id == sticker_unique_id).first():
            sticker = Sticker(file_id=sticker_id, file_unique_id=sticker_unique_id)
            db_sess.add(sticker)
            db_sess.commit()
            await update.message.reply_text(f'Загрузил. Жду стикер! Закончить: /end_sticker')
        else:
            await update.message.reply_text(f'Такой стикер уже есть, давай другой! Закончить: /end_sticker')
        db_sess.close()
        return self.step_upload

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None

    async def end_uploading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Ура! Готово!')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def send_random_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        db_sess = db_session.create_session()
        list_ = db_sess.query(Sticker).all()
        if list_:
            sticker = choice(list_)
            await context.bot.send_sticker(update.message.chat.id, sticker.file_id)
        db_sess.close()

    async def erase_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        db_sess = db_session.create_session()
        for stick in db_sess.query(Sticker).all():
            db_sess.delete(stick)
        db_sess.commit()
        db_sess.close()
        await update.message.reply_text('Очистил список стикеров!')
