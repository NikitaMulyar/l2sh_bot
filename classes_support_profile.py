from funcs_back import *
from telegram import KeyboardButton, ReplyKeyboardMarkup

class Profile:
    async def timetable_kbrd(self):
        btn = KeyboardButton('📚Расписание📚')
        kbd = ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
        return kbd

    async def get_profile(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполни свои данные')
            return
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        t = f'📠*Ваш профиль*📠\n\n' + (f'Класс: {user.grade}\nИмя: {user.name}\n'
                                      f'Фамилия: {user.surname}')
        await update.message.reply_text(t, parse_mode='MarkdownV2',
                                        reply_markup=await self.timetable_kbrd())


class Support:
    async def timetable_kbrd(self):
        btn = KeyboardButton('📚Расписание📚')
        kbd = ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
        return kbd

    async def get_supp(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh',
                                        reply_markup=await self.timetable_kbrd())
