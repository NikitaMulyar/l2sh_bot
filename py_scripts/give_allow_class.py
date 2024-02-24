from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy
from telegram.ext import ConversationHandler, ContextTypes
from telegram import ReplyKeyboardMarkup, Update
from sqlalchemy_scripts.users import User
import logging
from py_scripts.consts import COMMANDS
from sqlalchemy_scripts import db_session


class GivePermissionToChangePsw:
    step_get_username = 1
    step_confirm = 2

    async def confirm_kbd(self):
        kbd = ReplyKeyboardMarkup([['✅Да', '❌Нет']], resize_keyboard=True)
        return kbd

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        db_sess.close()
        if not user:
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return ConversationHandler.END
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            if not user.allow_changing:
                await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
                return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['give']])
        title = ('‼️ *ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ* ‼️\n\n'
                 '_Правила использования функции выдачи прав на сброс пароля_\n'
                '> 1\. Администрация бота *НЕ НЕСЕТ ответственности* за выдачу прав 3\-им лицам\n'
                '> 2\. Все попытки выдачи прав *ЗАПИСЫВАЮТСЯ* в файл на сервере\n'
                '> 3\. Пользователь, получивший данное право, может передавать его другим\!\n'
                '> 4\. Пожалуйста\, проверяйте\, кому вы даете права на сброс пароля\!')
        await update.message.reply_text(title, parse_mode='MarkdownV2')
        await update.message.reply_text('Введите username пользователя, которому вы хотите дать '
                                        'права на сброс пароля (пример: @username)\nПрерваться: /end_give')
        return self.step_get_username

    async def get_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        username = update.message.text
        username = username[1:] if username[0] == '@' else username
        username2 = '@' + username
        await update.message.reply_text(f'Вы хотите дать права на сброс пароля пользователю ' 
                                        f'*{prepare_for_markdown(username2)}* \?', parse_mode='MarkdownV2',
                                        reply_markup=await self.confirm_kbd())
        context.user_data['GIVE_USER_PERMIS'] = username
        return self.step_confirm

    async def get_confirmed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        username = context.user_data['GIVE_USER_PERMIS']
        username2 = '@' + username
        if update.message.text == '✅Да':
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.telegram_tag == username).first()
            if not user:
                await update.message.reply_text(f'⚠️ *Пользователь с именем {prepare_for_markdown(username2)} '
                                                f'не найден\.* Введите username пользователя\, которому '
                                                f'вы хотите дать права на сброс пароля \(пример\: '
                                                f'\@username\)\nПрерваться\: \/end\_give', parse_mode='MarkdownV2')
                return self.step_get_username
            if user.allow_changing:
                await update.message.reply_text(f'У пользователя {username2} уже есть данные права. '
                                                f'Начать сначала: /give', reply_markup=await timetable_kbrd())
                context.user_data['in_conversation'] = False
                context.user_data['DIALOG_CMD'] = None
                return ConversationHandler.END
            user.allow_changing = True
            db_sess.commit()
            author = db_sess.query(User).filter(User.chat_id == update.message.chat.id).first()
            db_sess.close()
            error_text = ''
            try:
                msg = await context.bot.send_message(user.chat_id, f'Пользователь *{prepare_for_markdown("@" + author.telegram_tag)}* выдал вам права на сброс пароля\.\n'
                                               f'Доступные команды\:\n'
                                               f'\/reset \- сброс пароля\n'
                                               f'\/give \- выдача прав на сброс пароля\n'
                                               f'\/end\_give \- закончить выдачу прав\n'
                                               f'\/take \- лишить пользователя права на сброс пароля\n'
                                               f'\/end\_take \- закончить лишение прав', parse_mode='MarkdownV2')
                await msg.pin()
            except Exception:
                error_text = '⚠️ *Пользователь не получил уведомление о получении права\!*'
            logging.warning(f'USER username: <{author.telegram_tag}> <{author.surname}> '
                             f'<{author.name}> (chat_id: <{author.chat_id}>, telegram_id: '
                             f'<{author.telegram_id}>) --->>> GAVE RIGHTS FOR PASSWORD RESETTING TO USER username: '
                             f'<{user.telegram_tag}> <{user.surname}> <{user.name}> (chat_id: '
                             f'<{user.chat_id}>, telegram_id: <{user.telegram_id}>)')
            await update.message.reply_text(
                f'Теперь *{prepare_for_markdown(username2)}* имеет право '
                f'менять пароль и выдавать такое право другим\!\n{error_text}', parse_mode='MarkdownV2')
        else:
            await update.message.reply_text('Выдача прав прервана')
        await update.message.reply_text('Начать сначала: /give', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def end_give(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Выдача прав прервана. Начать сначала: /give', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
