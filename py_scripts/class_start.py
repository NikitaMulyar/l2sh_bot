from telegram.ext import ConversationHandler
from telegram import ReplyKeyboardRemove
from funcs_back import *


class SetTimetable:
    step_class = 1
    step_familia = 2
    step_name = 3
    step_pswrd = 4
    step_third_name = 5
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']

    async def classes_buttons(self):
        classes = [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)] + [['АДМИН']]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            user = db_sess.query(User).filter(User.telegram_id == user__id).first()
            user.chat_id = update.message.chat.id
            db_sess.commit()
            await update.message.reply_text(
                'Привет! Я вижу, что Вы уже есть в системе.\n'
                'Теперь Вы можете пользоваться ботом.\n'
                'Все команды бота доступны в кнопке "Меню"',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        else:
            await update.message.reply_text('Если Вы из пед. состава, выберите кнопку "АДМИН"')
            await update.message.reply_text(
                'Привет! В этом боте Вы можете узнавать свое расписание на день!\n'
                'Но сначала немного формальностей - выберите свой класс.\n'
                'Если захотите остановить регистрацию, напишите: /end', reply_markup=await self.classes_buttons())
            context.user_data['INFO'] = dict()
            return self.step_class

    async def get_class(self, update, context):
        user__id = update.message.from_user.id
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if user:
            if update.message.text == 'АДМИН' and user.grade != 'АДМИН':
                context.user_data['INFO']['Class'] = update.message.text
                await update.message.reply_text('Введите пароль админа:',
                                                reply_markup=ReplyKeyboardRemove())
                return self.step_pswrd
        elif update.message.text == 'АДМИН':
            context.user_data['INFO']['Class'] = update.message.text
            await update.message.reply_text('Введите пароль админа:',
                                                reply_markup=ReplyKeyboardRemove())
            return self.step_pswrd
        if update.message.text != 'АДМИН' and update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        context.user_data['INFO']['Class'] = update.message.text
        await update.message.reply_text(f'А теперь укажите свою фамилию (пример: Некрасов)',
                                                reply_markup=ReplyKeyboardRemove())
        return self.step_familia

    async def get_psw(self, update, context):
        if hash(update.message.text) != password_hash:
            await update.message.reply_text('Неверный пароль. Настройка данных прервана. '
                                            'Начать сначала: /start',
                                            reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            return ConversationHandler.END
        await update.message.reply_text(f'А теперь укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update, context):
        context.user_data['INFO']['Familia'] = update.message.text
        await update.message.reply_text(f'А теперь укажите свое ПОЛНОЕ имя (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        if context.user_data['INFO']['Class'] == 'АДМИН':
            await update.message.reply_text(f'Напишите, пожалуйста, свое отчество')
            return self.step_third_name
        put_to_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def get_third_name(self, update, context):
        context.user_data['INFO']['Otchestvo'] = update.message.text
        put_to_db(update, context.user_data['INFO']['Name'] + ' ' +
                  context.user_data['INFO']['Otchestvo'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Регистрация в системе прервана. Начать сначала: /start',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
