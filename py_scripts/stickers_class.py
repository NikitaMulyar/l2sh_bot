from py_scripts.funcs_back import db_sess, bot, throttle, check_busy
from telegram.ext import ConversationHandler
from sqlalchemy_scripts.stickers_table import Sticker
from random import choice
from sqlalchemy_scripts.users import User
from py_scripts.consts import COMMANDS


class GetSticker:
    step_upload = 1

    async def start(self, update, context):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(
                f'У вас нет прав использовать данную команду.')
            return ConversationHandler.END
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            await update.message.reply_text(
                f'У вас нет прав использовать данную команду.')
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['sticker']
        await update.message.reply_text(f'Жду стикер! Закончить: /stick_end')
        return self.step_upload

    @throttle()
    async def get_sticker(self, update, context):
        sticker_id = update.message.sticker.file_id
        sticker_unique_id = update.message.sticker.file_unique_id
        if not db_sess.query(Sticker).filter(Sticker.file_unique_id == sticker_unique_id).first():
            sticker = Sticker(file_id=sticker_id, file_unique_id=sticker_unique_id)
            db_sess.add(sticker)
            db_sess.commit()
            await update.message.reply_text(f'Загрузил. Жду стикер! Закончить: /stick_end')
        else:
            await update.message.reply_text(f'Такой стикер уже есть, давай другой! Закончить: /stick_end')
        return self.step_upload

    async def end_uploading(self, update, context):
        await update.message.reply_text('Ура! Готово!')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def send_random_sticker(self, update, context):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        list_ = db_sess.query(Sticker).all()
        if list_:
            sticker = choice(list_)
            await bot.send_sticker(update.message.chat.id, sticker.file_id)

    async def erase_all(self, update, context):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        for stick in db_sess.query(Sticker).all():
            db_sess.delete(stick)
        db_sess.commit()
        await update.message.reply_text('Очистил список стикеров!')
