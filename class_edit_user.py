from class_start import *


class Edit_User(SetTimetable):
    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            db_sess.close()
            await update.message.reply_text('Давай начнём изменять информацию о тебе.\n'
                                            'Напиши свой класс: (пример: 7Г)')
            return self.step_class
        else:
            db_sess.close()
            context.user_data['in_conversation'] = False
            await update.message.reply_text(f'Ты даже не заполнил(а) свои данные. Напиши /start и заполни свои данные')
            return ConversationHandler.END

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        update_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь ты можешь пользоваться ботом',
                                        reply_markup=await self.timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
