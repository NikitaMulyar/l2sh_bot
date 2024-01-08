import random
import hashlib
from sqlalchemy_scripts.users import User
import logging
from py_scripts.funcs_back import bot, timetable_kbrd, db_sess, prepare_for_markdown


class Reset_Class:
    async def reset_admin_password(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        chat_id = update.message.chat.id
        author = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not author:
            await update.message.reply_text(f'Нет доступа!')
            return
        if author.telegram_id != 562532936 and author.telegram_id != 871689175:
            if not author.allow_changing:
                await update.message.reply_text(f'Нет доступа!')
                return
        del_adm = db_sess.query(User).filter(User.allow_changing == 0, User.role == 'admin').all()
        for item in del_adm:
            db_sess.delete(item)
        db_sess.commit()
        passw = prepare_for_markdown(new_password())
        for user in del_adm:
            try:
                await bot.send_message(user.chat_id,
                                       "*Произошёл сброс пароля и очистка всех администраторов из базы данных\.\n"
                                       "Обратитесь в поддержку за новым паролем*" +
                                       prepare_for_markdown(': /support'),
                                       parse_mode='MarkdownV2')
            except Exception:
                continue
        admins = db_sess.query(User).filter((User.telegram_id == 562532936) | (User.telegram_id == 871689175)).all()
        inform_about_changing = (f'ПОЛЬЗОВАТЕЛЬ <{author.telegram_tag}> <{author.surname}> '
                                 f'<{author.name}> (chat_id: <{author.chat_id}>, telegram_id: '
                                 f'<{author.telegram_id}>) --->>> СМЕНИЛ ПАРОЛЬ')
        for user in admins:
            await bot.send_message(user.chat_id, prepare_for_markdown(inform_about_changing + '\n') +
                                   f"Новый пароль\: `{passw}`",  parse_mode='MarkdownV2')
        t = f"Произошёл сброс пароля и очистка всех администраторов из базы данных\.\nНовый пароль\: `{passw}`"
        logging.warning(inform_about_changing)
        await update.message.reply_text(t, reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')

    async def get_info_about_bot(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(f'Нет доступа!')
            return
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            if user.role != 'admin':
                await update.message.reply_text(f'Нет доступа!')
                return
        all_users = db_sess.query(User).all()
        with open('db_copy.txt', mode='w', encoding='utf-8') as f:
            i = 1
            for user_ in all_users:
                s = (f'{i}. @{user_.telegram_tag} {user_.surname} {user_.name} ' +
                     f'(chat_id: {user_.chat_id}, telegram_id: {user_.telegram_id})\n\n')
                f.write(s)
                i += 1
            f.close()
        await bot.send_document(chat_id, 'out/logs.log')
        await bot.send_document(chat_id, 'db_copy.txt')
        await bot.send_document(chat_id, 'database/telegram_bot.db')


def check_hash(password):
    with open('password', 'rt', encoding='utf-8') as f:
        password_hash = f.read()
    return my_hash(password) == password_hash


def new_password():
    chars = '+-/*!&$#?=@<>abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
    password = ''
    for i in range(12):
        password += random.choice(chars)
    with open('password', 'wt', encoding='utf-8') as f:
        f.write(my_hash(password))
    f.close()
    return password


def my_hash(text):
    try:
        hash_obj = hashlib.sha256(text.encode('ascii'))
        hex_hash = hash_obj.hexdigest()
        return hex_hash
    except Exception:
        return '402'
