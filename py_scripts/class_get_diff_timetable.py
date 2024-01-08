from telegram import ReplyKeyboardMarkup
from py_scripts.funcs_back import timetable_kbrd, throttle2
from telegram.ext import ConversationHandler
from py_scripts.timetable_back_funcs import (get_standard_timetable_with_edits_for_teacher,
                                             get_standard_timetable_with_edits_for_student)
from py_scripts.funcs_teachers import extra_send_day


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

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        await update.message.reply_text('С помощью этой команды можно быстро посмотреть расписание '
                                        'какого-то класса, ученика или учителя. Выберите из списка интересуемый класс.\n'
                                        'Прерваться: /end_check',
                                        reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update, context):
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

    async def get_familia(self, update, context):
        context.user_data['INFO']['Familia'] = update.message.text
        await update.message.reply_text(f'Укажите ПОЛНОЕ имя пользователя (пример: Николай)')
        return self.step_name

    async def get_name(self, update, context):
        context.user_data['INFO']['Name'] = update.message.text
        kbrd = await self.days_buttons()
        await update.message.reply_text('Выберите день недели для расписания',
                                        reply_markup=kbrd)
        return self.step_date

    @throttle2
    async def get_day(self, update, context):
        if update.message.text not in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
            kbrd = await self.days_buttons()
            await update.message.reply_text('Выберите день недели для расписания',
                                            reply_markup=kbrd)
            return self.step_date
        context.user_data['INFO']['Day'] = update.message.text
        if context.user_data['INFO']['Class'] == 'Учитель':
            send_text = await get_standard_timetable_with_edits_for_teacher(update, context,
                                                                            context.user_data['INFO']['Day'],
                                                                            context.user_data['INFO']['Name'],
                                                                            context.user_data['INFO']['Familia'])
            await update.message.reply_text(send_text, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
            await extra_send_day(update, flag=True)
        else:
            send_text = await get_standard_timetable_with_edits_for_student(update, context,
                                            context.user_data['INFO']['Day'],
                                            context.user_data['INFO']['Class'],
                                            context.user_data['INFO']['Name'],
                                            context.user_data['INFO']['Familia'])
            await update.message.reply_text(send_text, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        await update.message.reply_text('Выберите день или закончите выбор командой: /end_check')
        return self.step_date

    async def end_checking(self, update, context):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        await update.message.reply_text(f'Поиск ученика/учителя прерван. Начать сначала: /check',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
