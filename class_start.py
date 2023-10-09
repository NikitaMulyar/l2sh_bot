from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from funcs_back import *


class SetTimetable:
    step_class = 1
    step_familia = 2
    step_name = 3
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']
    grade = ""
    name = ""
    surname = ""

    async def timetable_kbrd(self):
        btn = KeyboardButton('📚Расписание📚')
        kbd = ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        context.user_data['in_conversation'] = True
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            await update.message.reply_text(
                'Привет! Я вижу, что ты уже есть в системе.\n'
                'Теперь ты можешь пользоваться ботом',
                reply_markup=await self.timetable_kbrd())
            context.user_data['in_conversation'] = False
            context.user_data['last'] = True
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                'Привет! В этом боте ты можешь узнавать свое расписание на день!\n'
                'Но сначала немного формальностей: напиши свой класс (пример: 7Г)',
                reply_markup=ReplyKeyboardRemove())
            # context.user_data['INFO'] = dict()
            return self.step_class

    async def get_class(self, update, context):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        # context.user_data['INFO']['Class'] = update.message.text
        self.grade = update.message.text
        await update.message.reply_text(f'А теперь укажи свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update, context):
        # context.user_data['INFO']['Familia'] = update.message.text
        self.surname = update.message.text
        await update.message.reply_text(f'А теперь укажи свое ПОЛНОЕ имя (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        # context.user_data['INFO']['Name'] = update.message.text
        self.name = update.message.text
        put_to_db(update, self.name, self.surname, self.grade)
        await update.message.reply_text(f'Спасибо! Теперь ты можешь пользоваться ботом',
                                        reply_markup=await self.timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['last'] = True
        return ConversationHandler.END

    async def end_setting(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        context.user_data['last'] = False
        await update.message.reply_text(f'Настройка данных ученика сброшена. Начать сначала: /start')
