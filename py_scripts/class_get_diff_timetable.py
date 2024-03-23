from telegram import ReplyKeyboardMarkup, Update
from py_scripts.funcs_back import timetable_kbrd, throttle2, check_busy, prepare_for_markdown
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from py_scripts.funcs_students import get_standard_timetable_with_edits_for_student
from py_scripts.funcs_teachers import get_standard_timetable_with_edits_for_teacher
from py_scripts.funcs_extra_lessons import extra_send_day, extra_lessons_student_by_name


class CheckStudentTT:
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД'] + ['Учитель']
    step_class = 1
    step_familia = 2
    step_name = 3
    step_date = 4

    async def classes_buttons(self):
        classes = [["Учитель"]] + [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True, one_time_keyboard=True)
        return kbd

    async def days_buttons(self):
        arr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
        kbd = ReplyKeyboardMarkup([arr], resize_keyboard=True)
        return kbd

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['check']])
        await update.message.reply_text('С помощью этой команды можно быстро посмотреть расписание '
                                        'какого-то класса, ученика или учителя. Выберите из списка интересуемый класс.\n'
                                        'Прерваться: /end_check',
                                        reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text not in self.classes:
            await update.message.reply_text(
                f'⚠️ *Указан неверный класс \"{prepare_for_markdown(update.message.text)}\"*',
                reply_markup=await self.classes_buttons(),
                parse_mode='MarkdownV2')
            return self.step_class
        context.user_data['INFO']['Class'] = update.message.text
        if "6" <= update.message.text[:-1] <= "9":
            kbrd = await self.days_buttons()
            await update.message.reply_text('Выберите день недели для расписания',
                                            reply_markup=kbrd)
            context.user_data['INFO']['Name'] = ''
            context.user_data['INFO']['Familia'] = ''
            return self.step_date
        await update.message.reply_text(f'Укажите фамилию пользователя (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['INFO']['Familia'] = update.message.text.replace('ё', 'е')
        app_ = ''
        if context.user_data['INFO']['Class'] == 'Учитель':
            app_ = '(или первую букву полного имени) '
        await update.message.reply_text(f'Укажите ПОЛНОЕ имя пользователя {app_}(пример: Николай)')
        return self.step_name

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['INFO']['Name'] = update.message.text.replace('ё', 'е')
        kbrd = await self.days_buttons()
        await update.message.reply_text('Выберите день недели для расписания',
                                        reply_markup=kbrd)
        return self.step_date

    @throttle2()
    async def get_day(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text not in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
            kbrd = await self.days_buttons()
            await update.message.reply_text('Выберите день недели для расписания',
                                            reply_markup=kbrd)
            return self.step_date
        context.user_data['INFO']['Day'] = update.message.text
        if context.user_data['INFO']['Class'] == 'Учитель':
            send_text = await get_standard_timetable_with_edits_for_teacher(context.user_data['INFO']['Day'],
                                                                            context.user_data['INFO']['Name'],
                                                                            context.user_data['INFO']['Familia'])
            if len(send_text) == 1:
                await update.message.reply_text(send_text[0], parse_mode='MarkdownV2')
            else:
                total_len = len(send_text[0])
                ind = 0
                while ind < len(send_text[1]) and total_len + len(send_text[1][ind]) < 4000:
                    total_len += len(send_text[1][ind])
                    ind += 1
                await update.message.reply_text(send_text[0] + "".join(send_text[1][:ind]),
                                                parse_mode='MarkdownV2')
                scnd = "".join(send_text[1][ind:])
                if scnd:
                    await update.message.reply_text(scnd, parse_mode='MarkdownV2')
            await extra_send_day(update, surname=context.user_data['INFO']['Familia'], flag=True, no_kbrd=True)
        else:
            send_text = await get_standard_timetable_with_edits_for_student(context.user_data['INFO']['Day'],
                                                                            context.user_data['INFO']['Class'],
                                                                            context.user_data['INFO']['Name'],
                                                                            context.user_data['INFO']['Familia'])
            if len(send_text) == 1:
                await update.message.reply_text(send_text[0], parse_mode='MarkdownV2')
            else:
                total_len = len(send_text[0])
                ind = 0
                while ind < len(send_text[1]) and total_len + len(send_text[1][ind]) < 4000:
                    total_len += len(send_text[1][ind])
                    ind += 1
                await update.message.reply_text(send_text[0] + "".join(send_text[1][:ind]),
                                                parse_mode='MarkdownV2')
                scnd = "".join(send_text[1][ind:])
                if scnd:
                    await update.message.reply_text(scnd, parse_mode='MarkdownV2')
            await extra_lessons_student_by_name(update, button_text=context.user_data['INFO']['Day'],
                                                name=context.user_data['INFO']['Name'],
                                                surname=context.user_data['INFO']['Familia'])
        await update.message.reply_text('Выберите день или закончите выбор командой: /end_check')
        return self.step_date

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data["DIALOG_CMD"] = None
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()

    async def end_checking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        context.user_data['DIALOG_CMD'] = None
        await update.message.reply_text(f'Поиск ученика/учителя прерван. Начать сначала: /check',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
