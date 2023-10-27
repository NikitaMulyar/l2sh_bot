from class_start import *


class Edit_User(SetTimetable):
    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text('Если Вы из пед. состава, укажите вместо класса "АДМИН" (без кавычек)')
            await update.message.reply_text('Давайте начнём изменять информацию о Вас.\n'
                                            'Напишите свой класс: (пример: 7Г)\n'
                                            'Если захотите остановить изменения, напишите: /end_edit')
            context.user_data['INFO'] = dict()
            return self.step_class
        else:
            context.user_data['in_conversation'] = False
            await update.message.reply_text(f'Вы даже не заполнили свои данные. Напишите /start и заполните свои данные')
            return ConversationHandler.END

    async def get_psw(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Настройка данных прервана. '
                                            'Начать сначала: /edit')
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            return ConversationHandler.END
        await update.message.reply_text(f'А теперь укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_name(self, update, context):
        user__id = update.message.from_user.id
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if user.grade != context.user_data['INFO']['Class']:
            extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == user__id).all()
            for extra_lesson in extra_lessons:
                db_sess.delete(extra_lesson)
            db_sess.commit()
            await update.message.reply_text('Вы поменяли класс, поэтому все настройки кружков сброшены')
        context.user_data['INFO']['Name'] = update.message.text
        update_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Настройка данных ученика сброшена. Начать сначала: /edit')
        return ConversationHandler.END
