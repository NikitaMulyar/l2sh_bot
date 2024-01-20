from py_scripts.funcs_back import (throttle, db_sess, timetable_kbrd, prepare_for_markdown,
                                   check_busy)
from sqlalchemy_scripts.users import User
from telegram import Update
from telegram.ext import ContextTypes


class Profile:
    @throttle()
    async def get_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(f'Для начала заполните свои данные: /start')
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
        await update.message.reply_text(t, parse_mode='MarkdownV2',
                                        reply_markup=await timetable_kbrd())


class Support:
    @throttle()
    async def get_supp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh',
                                        reply_markup=await timetable_kbrd())
