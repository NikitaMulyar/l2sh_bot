import random
import hashlib
from sqlalchemy_scripts.users import User
import logging
from py_scripts.funcs_back import timetable_kbrd, prepare_for_markdown, check_busy
from telegram.ext import ContextTypes
from telegram import Update
from sqlalchemy_scripts import db_session


class Reset_Class:
    async def reset_admin_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        chat_id = update.message.chat.id
        db_sess = db_session.create_session()
        author = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not author:
            db_sess.close()
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return
        if author.telegram_id != 562532936 and author.telegram_id != 871689175:
            if not author.allow_changing:
                db_sess.close()
                await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
                return
        del_adm = db_sess.query(User).filter(User.allow_changing == 0, User.role == 'admin').all()
        for item in del_adm:
            db_sess.delete(item)
        db_sess.commit()
        passw = prepare_for_markdown(new_password())
        for user in del_adm:
            try:
                await context.bot.send_message(user.chat_id,
                                       "*Админский пароль был сброшен\. Все админы удалены из базы данных\.\n"
                                       "Обратитесь в поддержку за новым паролем*\: \/support",
                                       parse_mode='MarkdownV2')
            except Exception:
                continue
        admins = db_sess.query(User).filter((User.telegram_id == 562532936) | (User.telegram_id == 871689175)).all()
        inform_about_changing = (f'USER username: <{author.telegram_tag}> <{author.surname}> '
                                 f'<{author.name}> (chat_id: <{author.chat_id}>, telegram_id: '
                                 f'<{author.telegram_id}>) --->>> RESET PASSWROD')
        for user in admins:
            msg = await context.bot.send_message(user.chat_id, prepare_for_markdown(inform_about_changing + '\n') +
                                   f"Новый пароль\: `{passw}`",  parse_mode='MarkdownV2')
            await msg.pin()
        t = f"Админский пароль был сброшен\. Все админы удалены из базы данных\.\nНовый пароль\: `{passw}`"
        logging.warning(inform_about_changing)
        await update.message.reply_text(t, reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        for user in db_sess.query(User).filter(User.allow_changing == 1).all():
            try:
                msg = await context.bot.send_message(user.chat_id, t, parse_mode='MarkdownV2')
                await msg.pin()
            except Exception:
                continue
        db_sess.close()

    async def get_info_about_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        chat_id = update.message.chat.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            db_sess.close()
            await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
            return
        if user.telegram_id != 562532936 and user.telegram_id != 871689175:
            if user.role != 'admin':
                db_sess.close()
                await update.message.reply_text('⚠️ *Нет доступа\!*', parse_mode='MarkdownV2')
                return
        all_users = db_sess.query(User).all()
        all_users = sorted(all_users, key=lambda t: (t.role, t.grade))
        with open('bot_files/db_copy.txt', mode='w', encoding='utf-8') as f:
            i = 1
            for user_ in all_users:
                s = (f'{i}. @{user_.telegram_tag} {user_.surname} {user_.name} ' +
                     f'(chat_id: {user_.chat_id}, tg_id: {user_.telegram_id}, uid: {user_.uid}) '
                     f'{user_.role} {user_.grade}\n\n')
                f.write(s)
                i += 1
        f.close()
        db_sess.close()
        await context.bot.send_document(chat_id, 'out/logs.log')
        await context.bot.send_document(chat_id, 'bot_files/db_copy.txt')
        await context.bot.send_document(chat_id, 'database/telegram_bot.db')


def check_hash(password):
    with open('password', 'rt', encoding='utf-8') as f:
        password_hash = f.read()
    f.close()
    return my_hash(password) == password_hash


def new_password():
    chars = '+-/*!&$#?=@<>abcdefghijknpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
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
