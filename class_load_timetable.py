from telegram.ext import ConversationHandler
from funcs_back import *
from timetables_csv import *


class LoadTimetables:
    step_pswrd = 1
    step_class = 2
    step_file = 3
    classes = ['6-9'] + [f'{i}{j}' for i in range(10, 12) for j in 'АБВГД']

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        user = db_sess.query(User).filter(User.telegram_id == update.message.chat.id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_load')
        if user and user.grade == 'АДМИН':
            await update.message.reply_text(f'Укажите класс\n⚠️Если расписание 6-9 классов, то нужно указать без кавычек: '
                                        f'"6-9". Для 10, 11 классов по-обычному: 10А, 10Д, 11Г и т.п.:')
            context.user_data['in_conversation'] = True
            return self.step_class
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Загрузка расписаний прервана. '
                                            'Начать сначала: /load')
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(f'Укажите класс\n⚠️Если расписание 6-9 классов, то нужно указать без кавычек: '
                                        f'"6-9". Для 10, 11 классов по-обычному: 10А, 10Д, 11Г и т.п.')
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
        #await write_all(bot, prepare_for_markdown('❕') + '_*Бот будет недоступен в течение 1-2 минут\.*_\n' +
        #                prepare_for_markdown(f"Производится загрузка нового расписания для {context.user_data['filename']} класса."),
        #                parse_mode='MarkdownV2')
        await file_info.download_to_drive(path_to_timetables +
                                          f"{context.user_data['filename']}.pdf")
        if context.user_data['filename'] == '6-9':
            await extract_timetable_for_students_6_9()
        else:
            await extract_timetable_for_students_10_11([context.user_data['filename']])
        await update.message.reply_text('Файл загружен. Завершить: /end_load')
        context.user_data['FILE_UPLOADED'] = True
        await update.message.reply_text(f'Укажите класс\n⚠️Если расписание 6-9 классов, то нужно указать без кавычек: '
                                        f'"6-9". Для 10, 11 классов по-обычному: 10А, 10Д, 11Г и т.п.:')
        return self.step_class

    async def end_setting(self, update, context):
        if context.user_data.get('FILE_UPLOADED'):
            await update.message.reply_text('Загрузка расписаний завершена. Проведена рассылка всем ученикам об обновлении расписаний.',
                                            reply_markup=await timetable_kbrd())
            await write_all(bot, prepare_for_markdown('❕') + '_*Уважаемые лицеисты\!*_' +
                            prepare_for_markdown('\nОбновлены расписания. Пожалуйста, проверьте ваше расписание!'),
                            parse_mode='MarkdownV2')
        else:
            await update.message.reply_text('Загрузка расписаний завершена.', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['FILE_UPLOADED'] = False
        return ConversationHandler.END


class LoadEditsTT:
    step_pswrd = 1
    step_date = 2
    step_file = 3

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        user = db_sess.query(User).filter(User.telegram_id == update.message.chat.id).first()
        await update.message.reply_text('Прервать загрузку расписаний: /end_changes')
        if user and user.grade == 'АДМИН':
            await update.message.reply_text(f'Укажите дату изменений в расписании (формат: ДД.ММ.ГГГГ):')
            context.user_data['in_conversation'] = True
            return self.step_date
        await update.message.reply_text('Введите пароль админа:')
        context.user_data['in_conversation'] = True
        return self.step_pswrd

    async def get_pswrd(self, update, context):
        if update.message.text != password:
            await update.message.reply_text('Неверный пароль. Загрузка расписаний прервана. '
                                            'Начать сначала: /load')
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        await update.message.reply_text(f'Укажите дату изменений в расписании (формат: ДД.ММ.ГГГГ):')
        return self.step_date

    async def get_date(self, update, context):
        if len(update.message.text.split('.')) != 3 or not all([i.isdigit() for i in update.message.text.split('.')]):
            await update.message.reply_text(f'Указана неверная дата "{update.message.text}"')
            return self.step_date
        context.user_data['changes_date'] = update.message.text
        await update.message.reply_text(f'Загрузите файл .pdf')
        return self.step_file

    async def load_pdf(self, update, context):
        file_info = await bot.get_file(update.message.document.file_id)
        # await clear_the_changes_folder()
        await file_info.download_to_drive(path_to_changes + f"{context.user_data['changes_date']}.pdf")
        await update.message.reply_text('Файл загружен. Проведена рассылка всем ученикам об обновлении расписаний.')
        await write_all(bot, prepare_for_markdown('❕') + '_*Уважаемые лицеисты\!*_' +
                        prepare_for_markdown(
                            '\nВ боте появились изменения в расписании на ближайший учебный день. '
                            'Пожалуйста, проверьте ваше расписание на ближайший учебный день!'),
                        parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        return ConversationHandler.END

    async def end_setting(self, update, context):
        await update.message.reply_text('Загрузка изменений в расписании прервана',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
