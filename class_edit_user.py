from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from funcs_back import *
from class_start import *


class Edit_User(SetTimetable):
    async def start(self, update, context):
        context.user_data['in_conversation'] = True
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            db_sess.close()
            await update.message.reply_text('Давай начнём изменять информацию.\n'
                                            'Напиши свой класс')
            return self.step_class
        else:
            db_sess.close()
            await update.message.reply_text(f'Ты даже не заполнил свои данные. Напиши /start и зарегистрируйся')
            return ConversationHandler.END

    async def get_name(self, update, context):
        # context.user_data['INFO']['Name'] = update.message.text
        self.name = update.message.text
        update_db(update, self.name, self.surname, self.grade)
        await update.message.reply_text(f'Спасибо! Теперь ты снова можешь пользоваться ботом',
                                        reply_markup=await self.timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['last'] = True
        return ConversationHandler.END
