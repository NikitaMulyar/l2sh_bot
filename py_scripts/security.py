import random
import hashlib
from sqlalchemy_scripts.users import User

from py_scripts.funcs_back import bot, timetable_kbrd, db_sess


class Reset_Class:
    async def reset_admin_password(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user or not user.allow_changing:
            await update.message.reply_text(f'Нет доступа!')
            return
        del_adm = db_sess.query(User).filter(User.allow_changing == 0, User.role == 'admin').all()
        for item in del_adm:
            db_sess.delete(item)
        db_sess.commit()
        for user in del_adm:
            try:
                await bot.send_message(user.chat_id,
                                       "Произошёл сброс пароля и очистка всех администраторов из базы данных.\n"
                                       "Обратитесь в поддержку за новым паролем",
                                       parse_mode='MarkdownV2')
            except Exception:
                continue
        passw = new_password()
        t = f"Произошёл сброс пароля и очистка всех администраторов из базы данных \n Новый пароль: {passw}"
        await update.message.reply_text(t, reply_markup=await timetable_kbrd())


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
    return password


def my_hash(text):
    try:
        hash_obj = hashlib.sha256(text.encode('ascii'))
        hex_hash = hash_obj.hexdigest()
        return hex_hash
    except Exception:
        return '402'
