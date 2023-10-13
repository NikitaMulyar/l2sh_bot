from funcs_back import *


class Profile:
    @throttle
    async def get_profile(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if not db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(f'Для начала заполни свои данные: /start')
            return
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if not user:
            db_sess.close()
            await update.message.reply_text(
                f'Ты даже не заполнил(а) свои данные. Напиши /start и заполни свои данные')
            return
        t = f'📠*Ваш профиль*📠\n\n' + (f'Класс: {user.grade}\nИмя: {user.name}\n'
                                      f'Фамилия: {user.surname}')
        db_sess.close()
        await update.message.reply_text(t, parse_mode='MarkdownV2',
                                        reply_markup=await timetable_kbrd())


class Support:
    @throttle
    async def get_supp(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh',
                                        reply_markup=await timetable_kbrd())
