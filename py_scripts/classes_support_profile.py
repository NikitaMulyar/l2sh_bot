from py_scripts.funcs_back import throttle, db_sess, timetable_kbrd, prepare_for_markdown
from sqlalchemy_scripts.users import User


class Profile:
    @throttle()
    async def get_profile(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(f'Для начала заполните свои данные: /start')
            return
        grade = user.grade
        if not grade:
            if user.role == "teacher":
                grade = "Учитель"
            else:
                grade = "Админ"
        t = (f'📠*Ваш профиль*📠\n\n' +
             prepare_for_markdown(f'Класс: {grade}\nИмя: {user.name}\nФамилия: {user.surname}\n'
                                  f'Роль: {user.role}'))
        await update.message.reply_text(t, parse_mode='MarkdownV2',
                                        reply_markup=await timetable_kbrd())


class Support:
    @throttle()
    async def get_supp(self, update, context):
        await update.message.reply_text('Чат тех-поддержки: @help_group_l2sh',
                                        reply_markup=await timetable_kbrd())
