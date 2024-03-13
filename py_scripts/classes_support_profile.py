from py_scripts.funcs_back import (throttle, timetable_kbrd, prepare_for_markdown,
                                   check_busy)
from sqlalchemy_scripts.users import User
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy_scripts import db_session


class Profile:
    @throttle(seconds=3)
    async def get_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        chat_id = update.message.chat.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        user.telegram_tag = update.message.from_user.username
        db_sess.commit()
        if not user:
            await update.message.reply_text('⚠️ *Для начала заполните свои данные\: \/start*',
                                            parse_mode='MarkdownV2')
            db_sess.close()
            return
        grade = user.grade
        role = "Ученик"
        if not grade:
            if user.role == "teacher":
                grade = "Учитель"
                role = "Учитель"
            else:
                grade = "Админ"
                role = "Админ"

        t = (f'📠*Ваш профиль*📠\n\n' +
             prepare_for_markdown(f'Класс: {grade}\nИмя: {user.name}\nФамилия: {user.surname}\n'
                                  f'Роль: {role}'))
        await update.message.reply_text(t + f'\nUID\: `{user.uid}`', parse_mode='MarkdownV2')
        db_sess.close()


class Support:
    @throttle(seconds=3)
    async def get_supp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh\n'
                                        'Админы: @delikatny_pon (Никита), @lokisf8 (Матвей)')
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == update.message.chat_id).first()
        if user is None:
            db_sess.close()
            return
        try:
            await update.message.reply_document(f'bot_files/{user.role}.pdf',
                                                caption='Рекомендуем ознакомиться с '
                                                        'руководством пользователя!')
        except Exception:
            pass
        db_sess.close()
