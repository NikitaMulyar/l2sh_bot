from funcs_back import *
from telegram.ext import ConversationHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from server import bot
from consts import *

class LoadTimetables:
    step_pswrd = 1
    step_class = 2
    step_file = 3
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД']

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Загрузка расписаний прервана. '
                                            'Начать сначала: /load')
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(f'Укажите класс (пример: 7Г):')
        return self.step_class

    async def get_class(self, update, context):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
            return self.step_class
        context.user_data['filename'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update, context):
        file_info = await bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(path_to_timetables +
                                                 f"{context.user_data['filename']}.pdf")
        await update.message.reply_text('Файл загружен.')
        await update.message.reply_text(f'Укажите класс (пример: 7Г):')
        return self.step_class

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка расписаний завершена')
        return ConversationHandler.END
