import asyncio
import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from class_timetable import *
from class_edit_user import *
from class_mailing import *
from class_start import *
from class_load_timetable import *
from classes_support_profile import *
from class_extra_lesson import *


logging.basicConfig(
    filename='out/logs.log', filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN)


def main():
    try:
        if not os.path.exists('out/'):
            os.mkdir("out/")
    except Exception:
        pass

    asyncio.run(write_all(bot, '🔋Бот был перезапущен. Все диалоги сброшены. '
                                             'Необходимо использовать команду /start'))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(BOT_TOKEN).build()
    # .post_init(post_init)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    start_dialog = SetTimetable()
    timetable__ = GetTimetable()
    edit_user_class = Edit_User()
    mail_dialog = MailTo()
    load_tt = LoadTimetables()
    extra_lesson_dialog = Extra_Lessons()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_name)]
        },
        fallbacks=[CommandHandler('end', start_dialog.end_setting)]
    )
    edit_user_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_user_class.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_name)]
        },
        fallbacks=[CommandHandler('end_edit', edit_user_class.end_setting)]
    )
    mailto_handler = ConversationHandler(
        entry_points=[CommandHandler('mail', mail_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_psw)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_parallel)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_class)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_text)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_author)]
        },
        fallbacks=[CommandHandler('end_mail', mail_dialog.end_mailing)]
    )
    load_tt_handler = ConversationHandler(
        entry_points=[CommandHandler('load', load_tt.start)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_tt.get_pswrd)],
                2: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_tt.get_class)],
                3: [MessageHandler(filters.Document.FileExtension('pdf'), load_tt.load_pdf)]},
        fallbacks=[CommandHandler('end_load', load_tt.end_setting)]
    )
    sup = Support()
    prof = Profile()
    sup_hadler = CommandHandler('support', sup.get_supp)
    prof_handler = CommandHandler('profile', prof.get_profile)
    timetable_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, timetable__.get_timetable)
    application.add_handlers(handlers={1: [conv_handler], 2: [timetable_handler], 3: [edit_user_handler],
                                       4: [mailto_handler], 5: [load_tt_handler],
                                       6: [prof_handler], 7: [sup_hadler]})
    try:
        application.run_polling()
    except Exception:
        write_all(bot, '🪫Бот остановлен.')


if __name__ == '__main__':
    db_session.global_init("database/telegram_bot.db")
    main()
