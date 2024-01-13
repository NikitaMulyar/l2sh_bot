from telegram.ext import ConversationHandler
from sqlalchemy_scripts.users import User
from py_scripts.class_start import SetTimetable
from py_scripts.funcs_back import update_db, db_sess, timetable_kbrd, check_busy
from sqlalchemy_scripts.user_to_extra import Extra_to_User
from py_scripts.consts import COMMANDS


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
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        chat_id = update.message.chat.id
        if not db_sess.query(User).filter(User.chat_id == chat_id).first():
            await update.message.reply_text(
                f'Вы даже не заполнили свои данные. Напишите /start и заполните свои данные')
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['edit']
        await update.message.reply_text('Давайте начнём изменять информацию о Вас.\n'
                                        'Выберите свою роль/класс.\n'
                                        'Если захотите остановить изменения, напишите: /end_edit',
                                        reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text.replace("ё", "е")
        if context.user_data['INFO']['Class'] == 'admin' or context.user_data['INFO']['Class'] == 'teacher':
            await update.message.reply_text(f'Напишите, пожалуйста, свое отчество')
            return self.step_third_name
        await clear_all_extra(update, context)
        update_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'], 'student',
                  update.message.from_user.username, grade=context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['INFO'] = dict()
        return ConversationHandler.END

    async def get_third_name(self, update, context):
        context.user_data['INFO']['Otchestvo'] = update.message.text.replace("ё", "е")
        await clear_all_extra(update, context)
        update_db(update, context.user_data['INFO']['Name'] + ' ' +
                  context.user_data['INFO']['Otchestvo'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'], update.message.from_user.username)
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['INFO'] = dict()
        return ConversationHandler.END
