from telegram.ext import ConversationHandler
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
from sqlalchemy_scripts.users import User
from py_scripts.consts import my_hash, password_hash
from py_scripts.funcs_back import db_sess, timetable_kbrd, put_to_db


class SetTimetable:
    step_class = 1
    step_familia = 2
    step_name = 3
    step_pswrd = 4
    step_third_name = 5
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД'] + ['Админ', 'Учитель']
    command = '/start'

    async def classes_buttons(self):
        classes = [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)] + [['Админ', 'Учитель']]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        chat_id = update.message.chat.id
        if db_sess.query(User).filter(User.chat_id == chat_id).first():
            db_sess.commit()
            await update.message.reply_text(
                'Здравствуйте! Я вижу, что Вы уже есть в системе.\n'
                'Можете пользоваться ботом.\n'
                'Все команды бота доступны в кнопке "Меню"',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(
            'Здравствуйте! В этом боте Вы можете узнавать расписание на день!\n'
            'Сначала выберите свою должность/класс.\n'
            'Для остановки регистрации напишите: /end', reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update, context):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if user and update.message.text == 'Админ' and user.role != "admin":
            context.user_data['INFO']['Class'] = "admin"
            await update.message.reply_text('Введите пароль:', reply_markup=ReplyKeyboardRemove())
            return self.step_pswrd
        elif update.message.text == 'Админ':
            context.user_data['INFO']['Class'] = "admin"
            await update.message.reply_text('Введите пароль:', reply_markup=ReplyKeyboardRemove())
            return self.step_pswrd
        if update.message.text == 'Учитель':
            context.user_data['INFO']['Class'] = "teacher"
        elif update.message.text == 'Админ':
            context.user_data['INFO']['Class'] = "admin"
        else:
            context.user_data['INFO']['Class'] = update.message.text
        await update.message.reply_text(f'Укажите свою фамилию (пример: Некрасов)',
                                        reply_markup=ReplyKeyboardRemove())
        return self.step_familia

    async def get_psw(self, update, context):
        if my_hash(update.message.text) != password_hash:
            await update.message.reply_text('Неверный пароль. Настройка данных прервана. '
                                            f'Начать сначала: {self.command}',
                                            reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            return ConversationHandler.END
        await update.message.reply_text(f'Укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update, context):
        context.user_data['INFO']['Familia'] = update.message.text
        await update.message.reply_text(f'Укажите свое ПОЛНОЕ имя (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        if context.user_data['INFO']['Class'] == 'admin' or context.user_data['INFO']['Class'] == 'teacher':
            await update.message.reply_text(f'Напишите, пожалуйста, свое отчество')
            return self.step_third_name
        put_to_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  'student', update.message.from_user.username, grade=context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def get_third_name(self, update, context):
        context.user_data['INFO']['Otchestvo'] = update.message.text
        put_to_db(update, context.user_data['INFO']['Name'] + ' ' +
                  context.user_data['INFO']['Otchestvo'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'], update.message.from_user.username)
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Регистрация в системе прервана. Начать сначала: {self.command}',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
