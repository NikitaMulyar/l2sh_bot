from telegram.ext import ConversationHandler

from py_scripts.security import my_hash, check_hash
from sqlalchemy_scripts.users import User
from py_scripts.class_start import SetTimetable
from py_scripts.funcs_back import update_db, db_sess, timetable_kbrd
from sqlalchemy_scripts.user_to_extra import Extra_to_User


async def clear_all_extra(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    user = db_sess.query(User).filter(User.chat_id == chat_id).first()
    if user.grade != context.user_data['INFO']['Class']:
        extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == user_id).all()
        for extra_lesson in extra_lessons:
            db_sess.delete(extra_lesson)
        db_sess.commit()
        await update.message.reply_text('Вы поменяли класс, поэтому все настройки кружков сброшены')


class Edit_User(SetTimetable):
    command = '/edit'

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        chat_id = update.message.chat.id
        if db_sess.query(User).filter(User.chat_id == chat_id).first():
            await update.message.reply_text('Давайте начнём изменять информацию о Вас.\n'
                                            'Выберите свою роль/класс.\n'
                                            'Если захотите остановить изменения, напишите: /end_edit',
                                            reply_markup=await self.classes_buttons())
            context.user_data['INFO'] = dict()
            return self.step_class
        else:
            context.user_data['in_conversation'] = False
            await update.message.reply_text(f'Вы даже не заполнили свои данные. Напишите /start и заполните свои данные')
            return ConversationHandler.END

    async def get_psw(self, update, context):
        if not check_hash(update.message.text):
            await update.message.reply_text('Неверный пароль. Настройка данных прервана. '
                                            'Начать сначала: /edit', reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            return ConversationHandler.END
        await update.message.reply_text(f'Укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        if context.user_data['INFO']['Class'] == 'admin' or context.user_data['INFO']['Class'] == 'teacher':
            await update.message.reply_text(f'Напишите, пожалуйста, свое отчество')
            return self.step_third_name
        await clear_all_extra(update, context)
        update_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'], 'student',
                  update.message.from_user.username, grade=context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def get_third_name(self, update, context):
        context.user_data['INFO']['Otchestvo'] = update.message.text
        await clear_all_extra(update, context)
        update_db(update, context.user_data['INFO']['Name'] + ' ' +
                  context.user_data['INFO']['Otchestvo'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'], update.message.from_user.username)
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
