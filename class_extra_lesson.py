from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from funcs_back import *
from data.user_to_extra import *


class Extra_Lessons:
    def __init__(self):
        days = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота"}
        self.count = {}
        for i in range(6):
            counter = 0
            extra_lessons = pd.read_excel('extra.xlsx', sheet_name=i, usecols=[2, 4, 6, 8, 10, 12]).values
            length = len(extra_lessons)
            for j in range(6):
                k = 1
                while k <= length:
                    if not pd.isnull(extra_lessons[k][j]):

                        title = extra_lessons[k][j]
                        place = extra_lessons[k + 4][j]
                        for l in range(1, 4):
                            if not pd.isnull(extra_lessons[k + l][j]):
                                if ("-" in extra_lessons[k + l][j] and "." in extra_lessons[k + l][j]) or (
                                        "переменах" in extra_lessons[k + l][j]):
                                    time = extra_lessons[k + l][j]
                                elif "Код" not in extra_lessons[k + l][j]:
                                    teacher = extra_lessons[k + l][j]
                        day = days[j]
                        extra = Extra(title=title, time=time, day=day, teacher=teacher, place=place, grade=i + 6)
                        if not bool(db_sess.query(Extra).filter(Extra.title == title, Extra.grade == i + 6,
                                                                Extra.day == day).first()):
                            db_sess.add(extra)
                        counter += 1
                    k += 6
            self.count[i + 6] = counter
        db_sess.commit()

    async def start(self, update, context):
        if context.user_data.get('in_conversation'):
            return ConversationHandler.END
        user__id = update.message.from_user.id
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if user.grade == 'АДМИН':
            await update.message.reply_text(f'⚠️У админов нет доступа к расписанию.')
            return
        await update.message.reply_text('🌟 Здесь Вы можете добавить кружки, которые хотели бы увидеть в '
                                        'своем расписании.\n'
                                        'Если захотите закончить, просто напишите: "/end_extra".\n'
                                        'Давайте начнем выбирать: ✨')
        context.user_data['in_conversation'] = True
        context.user_data['choose_count'] = 0
        return await self.choose_extra(update, context)

    async def choose_extra(self, update, context):
        if update.message:
            user__id = update.message.from_user.id
        else:
            user__id = update.callback_query.from_user.id
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        grade = user.number

        if context.user_data['choose_count'] == self.count[int(grade)]:
            await update.callback_query.edit_message_text('🌟 Загрузка кружков завершена! Большое спасибо за Ваш '
                                                          'выбор! 🙌🏻 Теперь Вы можете посмотреть своё расписание с кружками.',
                                                          reply_markup="")
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        lesson = list(db_sess.query(Extra).filter(Extra.grade == grade).all())[context.user_data['choose_count']]
        context.user_data['choose_count'] += 1
        while lesson.teacher.count(".") <= 1 and user.grade not in lesson.teacher:
            lesson = list(db_sess.query(Extra).filter(Extra.grade == grade).all())[context.user_data['choose_count']]
            context.user_data['choose_count'] += 1
        context.user_data['lesson'] = lesson
        place = ""
        if "зал" in lesson.place or "онлайн" in lesson.place:
            place = lesson.place
        else:
            place = f"{lesson.place} кабинет"
        text = f"""📅 {lesson.day} 📅\n {lesson.title} - {lesson.teacher} \n⏰ {lesson.time} ⏰\n🏫 {place} 🏫\nБудешь посещать?"""
        keyboard = [[InlineKeyboardButton("Да", callback_data="1"),
                     InlineKeyboardButton("Нет", callback_data="2")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        return 1

    async def yes_no(self, update, context):
        query = update.callback_query
        await query.answer()
        num = query.data
        user__id = query.from_user.id
        extra = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == user__id,
                                                    Extra_to_User.extra_id == context.user_data[
                                                        'lesson'].id).first()
        if num == '1':
            if not bool(extra):
                extra_to_user = Extra_to_User(user_id=user__id, extra_id=context.user_data['lesson'].id)
                db_sess.add(extra_to_user)
        else:
            if bool(extra):
                db_sess.delete(extra)
        db_sess.commit()
        return await self.choose_extra(update, context)

    async def get_out(self, update, context):
        await update.message.reply_text('🌟 Загрузка кружков завершена! Большое спасибо за Ваш '
                                        'выбор! 🙌🏻 Теперь Вы можете посмотреть своё расписание с кружками.',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        return ConversationHandler.END
