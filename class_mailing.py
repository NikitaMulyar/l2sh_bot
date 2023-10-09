from funcs_back import *
from telegram.ext import ConversationHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from server import bot


class MailTo:
    parallels = ['6', '7', '8', '9', '10', '11']
    classes = {f'{i}': [f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)}
    classes['6'] = ['6А', '6Б', '6В']
    step_pswrd = 1
    step_parallel = 2
    step_class = 3
    step_text = 4
    step_author = 5

    async def mailing_parallels_kbrd(self):
        btns = []
        for i in self.parallels:
            btns.append(KeyboardButton(i))

        kbd = ReplyKeyboardMarkup([[btns], [KeyboardButton('Всем')]], resize_keyboard=True)
        return kbd

    async def mailing_classes_kbrd(self, parallel):
        btns = []
        for i in self.classes[parallel]:
            btns.append(KeyboardButton(i))
        kbd = ReplyKeyboardMarkup([[btns], [KeyboardButton(f'Всем')]],
                                  resize_keyboard=True)
        return kbd

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_psw(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Настройка рассылки прервана. '
                                            'Начать сначала: /mailing')
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text('Выберите параллель, к которой будет обращена рассылка:',
                                        reply_markup=await self.mailing_parallels_kbrd())
        return self.step_parallel

    async def get_parallel(self, update, context):
        if update.message.text == 'Всем':
            context.user_data['PARAL'] = update.message.text
            context.user_data['CLASS'] = update.message.text
            await update.message.reply_text('Напишите сообщение для расслыки:',
                                            reply_markup=ReplyKeyboardRemove())
            return self.step_text
        if update.message.text not in self.parallels:
            await update.message.reply_text(
                'Выберите параллель, к которой будет обращена рассылка:',
                reply_markup=await self.mailing_parallels_kbrd())
            return self.step_parallel
        context.user_data['PARAL'] = update.message.text
        await update.message.reply_text('Выберите класс, к которому будет обращена рассылка:',
                                        reply_markup=await self.mailing_classes_kbrd(
                                            context.user_data['PARAL']))
        return self.step_class

    async def get_class(self, update, context):
        if update.message.text == 'Всем':
            context.user_data['CLASS'] = update.message.text
            await update.message.reply_text('Напишите сообщение для расслыки:',
                                            reply_markup=ReplyKeyboardRemove())
            return self.step_text
        classes = self.classes[context.user_data['PARAL']]
        if update.message.text not in classes:
            await update.message.reply_text(
                'Выберите класс, к которому будет обращена рассылка:',
                reply_markup=await self.mailing_classes_kbrd(context.user_data['PARAL']))
            return self.step_class
        context.user_data['CLASS'] = update.message.text
        await update.message.reply_text('Напишите сообщение для расслыки:',
                                        reply_markup=ReplyKeyboardRemove())
        return self.step_text

    async def get_text(self, update, context):
        context.user_data['MESSAGE'] = update.message.text
        await update.message.reply_text('Введите свои ФИО:')
        return self.step_author

    async def get_author(self, update, context):
        db_sess = db_session.create_session()
        all_users = db_sess.query(User).all()
        if context.user_data['PARAL'] != 'Всем':
            all_users = db_sess.query(User).filter(context.user_data['PARAL'] in User.grade).all()
            if context.user_data['CLASS'] != 'Всем':
                all_users = db_sess.query(User).filter(
                    context.user_data['CLASS'] == User.grade).all()
        for user in all_users:
            await bot.send_message(user.chat_id,
                                   context.user_data['MESSAGE'] + f'\n\nОт {update.message.text}')
        context.user_data['in_conversation'] = False
        p, c = context.user_data['PARAL'], context.user_data['CLASS']
        t = context.user_data['MESSAGE'] + f'\n\nОт {update.message.text}'
        await update.message.reply_text(f'Сообщение:\n"{t}"\n\nбыло отправлено в '
                                        f'параллель "{p}", класс: "{c}"')
        await update.message.reply_text('Настройка рассылки окончена. Начать сначала: /mailing')
        return ConversationHandler.END

    async def end_mailing(self, update, context):
        await update.message.reply_text('Настройка рассылки прервана. Начать сначала: /mailing')
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
