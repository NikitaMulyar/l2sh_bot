from funcs_back import *


class Profile:
    @throttle
    async def get_profile(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполните свои данные: /start')
            return
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if not user:
            await update.message.reply_text(
                f'Вы даже не заполнили свои данные. Напиши /start и заполните свои данные')
            return
        t = f'📠*Ваш профиль*📠\n\n' + (f'Класс: {user.grade}\nИмя: {user.name}\n'
                                      f'Фамилия: {user.surname}')
        await update.message.reply_text(t, parse_mode='MarkdownV2',
                                        reply_markup=await timetable_kbrd())


class Support:
    @throttle
    async def get_supp(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh',
                                        reply_markup=await timetable_kbrd())
