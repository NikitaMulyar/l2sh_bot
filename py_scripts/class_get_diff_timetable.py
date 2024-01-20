from telegram import ReplyKeyboardMarkup, Update
from py_scripts.funcs_back import timetable_kbrd, throttle2, check_busy
from py_scripts.consts import COMMANDS
from telegram.ext import ConversationHandler, ContextTypes
from py_scripts.funcs_students import get_standard_timetable_with_edits_for_student
from py_scripts.funcs_teachers import get_standard_timetable_with_edits_for_teacher
from py_scripts.funcs_extra_lessons import extra_send_day


class CheckStudentTT:
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД'] + ['Учитель']
    step_class = 1
    step_familia = 2
    step_name = 3
    step_date = 4

    async def classes_buttons(self):
        classes = [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)] + [["Учитель"]]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True)
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
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['check']
        await update.message.reply_text('С помощью этой команды можно быстро посмотреть расписание '
                                        'какого-то класса, ученика или учителя. Выберите из списка интересуемый класс.\n'
                                        'Прерваться: /end_check',
                                        reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'Указан неверный класс "{update.message.text}"')
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
        await update.message.reply_text(f'Укажите ПОЛНОЕ имя пользователя (пример: Николай)')
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
            send_text = await get_standard_timetable_with_edits_for_teacher(context,
                                                                            context.user_data['INFO']['Day'],
                                                                            context.user_data['INFO']['Name'],
                                                                            context.user_data['INFO']['Familia'])
            await update.message.reply_text(send_text, parse_mode='MarkdownV2')
            await extra_send_day(update, surname=context.user_data['INFO']['Familia'], flag=True, no_kbrd=True)
        else:
            send_text = await get_standard_timetable_with_edits_for_student(context,
                                            context.user_data['INFO']['Day'],
                                            context.user_data['INFO']['Class'],
                                            context.user_data['INFO']['Name'],
                                            context.user_data['INFO']['Familia'])
            await update.message.reply_text(send_text, parse_mode='MarkdownV2')
        await update.message.reply_text('Выберите день или закончите выбор командой: /end_check')
        return self.step_date

    async def end_checking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        context.user_data['DIALOG_CMD'] = None
        await update.message.reply_text(f'Поиск ученика/учителя прерван. Начать сначала: /check',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
