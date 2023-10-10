from telegram.ext import ConversationHandler
from funcs_back import *


class SetTimetable:
    step_class = 1
    step_familia = 2
    step_name = 3
    step_pswrd = 4
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        db_sess = db_session.create_session()
        user__id = update.message.from_user.id
        if db_sess.query(User).filter(User.telegram_id == user__id).first():
            user = db_sess.query(User).filter(User.telegram_id == user__id).first()
            user.chat_id = update.message.chat.id
            db_sess.commit()
            db_sess.close()
            await update.message.reply_text(
                'Привет! Я вижу, что ты уже есть в системе.\n'
                'Теперь ты можешь пользоваться ботом',
                reply_markup=await timetable_kbrd())
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        else:
            db_sess.close()
            await update.message.reply_text('Если вы из пед. состава, укажите вместо класса "АДМИН" (без кавычек)')
            await update.message.reply_text(
                'Привет! В этом боте ты можешь узнавать свое расписание на день!\n'
                'Но сначала немного формальностей: напиши свой класс (пример: 7Г)')
            context.user_data['INFO'] = dict()
            return self.step_class

    async def get_class(self, update, context):
        if update.message.text == 'АДМИН':
            context.user_data['INFO']['Class'] = update.message.text
            await update.message.reply_text('Введите пароль админа:')
            return self.step_pswrd
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        context.user_data['INFO']['Class'] = update.message.text
        await update.message.reply_text(f'А теперь укажи свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_psw(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Настройка данных прервана. '
                                            'Начать сначала: /start')
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            return ConversationHandler.END
        await update.message.reply_text(f'А теперь укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update, context):
        context.user_data['INFO']['Familia'] = update.message.text
        await update.message.reply_text(f'А теперь укажи(те) свое ПОЛНОЕ имя (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        put_to_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'])
        await update.message.reply_text(f'Спасибо! Теперь ты можешь пользоваться ботом',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Настройка данных ученика сброшена. Начать сначала: /start')
        return ConversationHandler.END
