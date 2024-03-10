from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from telegram import ReplyKeyboardMarkup, Update
from sqlalchemy_scripts.users import User
import logging
from sqlalchemy_scripts import db_session


class TakePermissionToChangePsw:
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
        if not user:
            db_sess.close()
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return ConversationHandler.END
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            if not user.allow_changing:
                db_sess.close()
                await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
                return ConversationHandler.END
        db_sess.close()
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['take']])
        title = ('‼️ *ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ* ‼️\n\n'
                 '_Правила использования функции выдачи прав на сброс пароля_\n'
                '> 1\. Администрация бота *НЕ НЕСЕТ ответственности* за лишение прав у 3\-их лиц\n'
                '> 2\. Все попытки лишения прав *ЗАПИСЫВАЮТСЯ* в файл на сервере\n')
        await update.message.reply_text(title, parse_mode='MarkdownV2')
        await update.message.reply_text('Введите UID пользователя, у которого вы хотите забрать '
                                        'права на сброс пароля (UID можно найти в Профиле по команде '
                                        '/profile)\nПрерваться: /end_take')
        return self.step_get_username

    async def get_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.message.text
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.uid == uid).first()
        if not user:
            await update.message.reply_text(f'⚠️ *Пользователь с UID {uid} '
                                            f'не найден\.* Введите UID пользователя\, у которого вы '
                                            f'хотите забрать права на сброс пароля \(UID можно найти '
                                            f'в Профиле по команде \/profile\)\nПрерваться\: '
                                            f'\/end\_take', parse_mode='MarkdownV2')
            return self.step_get_username
        if not user.allow_changing:
            await update.message.reply_text(f'У пользователя с UID {uid} уже нет данных прав. '
                                            f'Начать сначала: /take', reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        if user.telegram_tag is None:
            await update.message.reply_text(f'Вы хотите забрать права на сброс пароля пользователю с UID ' 
                                            f'*[{uid}](tg://user?id={user.telegram_id})* \?', parse_mode='MarkdownV2',
                                            reply_markup=await self.confirm_kbd())
        else:
            await update.message.reply_text(f'Вы хотите забрать права на сброс пароля пользователю с UID '
                                            f'*{uid} \(\@'
                                            f'{prepare_for_markdown(user.telegram_tag)}\)* \?', parse_mode='MarkdownV2',
                                            reply_markup=await self.confirm_kbd())
        context.user_data['GIVE_USER_PERMIS'] = uid
        return self.step_confirm

    async def get_confirmed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == '✅Да':
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.uid == context.user_data['GIVE_USER_PERMIS']).first()
            user.allow_changing = False
            db_sess.commit()
            author = db_sess.query(User).filter(User.chat_id == update.message.chat_id).first()
            error_text = ''
            try:
                if author.telegram_tag is None:
                    txt_ = f'*[{author.uid}](tg://user?id={author.telegram_id})*'
                else:
                    txt_ = f'*{author.uid} \(\@{prepare_for_markdown(author.telegram_tag)}\)*'
                await context.bot.send_message(user.chat_id, f'Пользователь {txt_} '
                                                           f'забрал у вас право на сброс пароля\.\n'
                                                           f'Если вы считаете\, что это ошибка \- напишите '
                                                           f'в тех\. поддержку \- \/support',
                                             parse_mode='MarkdownV2')
            except Exception as e:
                error_text = '⚠️ *Пользователь не получил уведомление о лишении прав\!*'
            logging.warning(f'USER username: <{author.telegram_tag}> <{author.surname}> '
                             f'<{author.name}> (chat_id: <{author.chat_id}>, telegram_id: '
                             f'<{author.telegram_id}>) --->>> TOOK RIGHTS FOR PASSWORD RESETTING AT USER '
                             f'<{user.telegram_tag}> <{user.surname}> <{user.name}> (chat_id: '
                             f'<{user.chat_id}>, telegram_id: <{user.telegram_id}>)')
            if user.telegram_tag is None:
                txt_ = f'*[{user.uid}](tg://user?id={user.telegram_id})*'
            else:
                txt_ = f'*{user.uid} \(\@{prepare_for_markdown(user.telegram_tag)}\)*'
            await update.message.reply_text(
                f'Теперь пользователь {txt_} _НЕ_ имеет право '
                f'менять пароль и выдавать такое право другим\.\n{error_text}', parse_mode='MarkdownV2')
        else:
            await update.message.reply_text('⚠️ *Процесс лишения прав прерван*', parse_mode='MarkdownV2')
        await update.message.reply_text('Начать сначала: /take', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None

    async def end_give(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Процесс лишения прав прерван. Начать сначала: /take',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
