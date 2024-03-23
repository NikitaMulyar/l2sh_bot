import logging
import os

import aiohttp
import telegram.ext
from telegram.ext import (Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, TypeHandler, PollAnswerHandler)
from telegram import Update
from py_scripts.class_timetable import GetTimetable
from py_scripts.class_edit_user import Edit_User
from py_scripts.class_mailing import MailTo
from py_scripts.class_start import SetTimetable
from py_scripts.class_load_timetable import LoadTimetables, LoadEditsTT
from py_scripts.classes_support_profile import Support, Profile
from py_scripts.class_extra_lesson import Extra_Lessons
from py_scripts.class_get_diff_timetable import CheckStudentTT
from py_scripts.config import BOT_TOKEN
from py_scripts.stickers_class import GetSticker
from py_scripts.security import Reset_Class
from py_scripts.give_allow_class import GivePermissionToChangePsw
from py_scripts.take_allow_class import TakePermissionToChangePsw
from sqlalchemy_scripts import db_session
import gc
import argparse
import asyncio
from py_scripts.timetables_csv import extract_timetable_for_students_6_9, extract_timetable_for_students_10_11
from py_scripts.funcs_teachers import extract_timetable_for_teachers
from py_scripts.wolfram_class import WolframClient
from py_scripts.game_class import GameMillioner
from py_scripts.class_load_extratable import Load_Extra_Table
from py_scripts.class_exams_checker import CheckClassExam, LoadHTMLExams

gc.enable()


try:
    if not os.path.exists('out/'):
        os.mkdir("out/")
    if not os.path.exists('changes_tt/'):
        os.mkdir("changes_tt/")
    if not os.path.exists('timetables/'):
        os.mkdir("timetables/")
    if not os.path.exists('timetables_csv/'):
        os.mkdir("timetables_csv/")

    if not os.path.exists('bot_files/db_copy.txt'):
        f = open('bot_files/db_copy.txt', mode='w', encoding='utf-8')
        f.write('')
        f.close()
    if not os.path.exists('bot_files/intensives.txt'):
        f = open('bot_files/intensives.txt', mode='w', encoding='utf-8')
        f.write('')
        f.close()
    if not os.path.exists('bot_files/list_mailing.txt'):
        f = open('bot_files/list_mailing.txt', mode='w', encoding='utf-8')
        f.write('')
        f.close()
    if not os.path.exists('bot_files/list_new_timetable.txt'):
        f = open('bot_files/list_new_timetable.txt', mode='w', encoding='utf-8')
        f.write('')
        f.close()
    if not os.path.exists('bot_files/logs_copy.txt'):
        f = open('bot_files/logs_copy.txt', mode='w', encoding='utf-8')
        f.write('')
        f.close()
except Exception:
    pass

logging.basicConfig(
    filename='out/logs.log', filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING,
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def main(do_update=False):
    application = (Application.builder().token(BOT_TOKEN).connection_pool_size(1024).read_timeout(10)
                   .write_timeout(10).connect_timeout(10).pool_timeout(10).build())
    start_dialog = SetTimetable()
    timetable__ = GetTimetable()
    edit_user_class = Edit_User()
    mail_dialog = MailTo()
    load_tt = LoadTimetables()
    load_changes_in_tt = LoadEditsTT()
    extra_lesson_dialog = Extra_Lessons()
    if do_update:
        asyncio.gather(extract_timetable_for_teachers(updating=True))
        asyncio.gather(extract_timetable_for_students_6_9(updating=True))
        asyncio.gather(extract_timetable_for_students_10_11(updating=True))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_psw)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_third_name)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, start_dialog.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, start_dialog.timeout_func)]
        },
        fallbacks=[CommandHandler('end', start_dialog.end_setting)],
        conversation_timeout=30
    )
    edit_user_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_user_class.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_psw)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_third_name)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, edit_user_class.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, edit_user_class.timeout_func)]
        },
        fallbacks=[CommandHandler('end_edit', edit_user_class.end_setting)],
        conversation_timeout=30
    )
    mailto_handler = ConversationHandler(
        entry_points=[CommandHandler('mail', mail_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_psw)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_parallel)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_class)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_text)],
            5: [MessageHandler(filters.Document.ALL, mail_dialog.get_attachments),
                MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_ready),
                MessageHandler(filters.AUDIO, mail_dialog.get_attachments)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, mail_dialog.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, mail_dialog.timeout_func)]
        },
        fallbacks=[CommandHandler('end_mail', mail_dialog.end_mailing)],
        conversation_timeout=120
    )
    load_tt_handler = ConversationHandler(
        entry_points=[CommandHandler('load', load_tt.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_tt.get_pswrd)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_tt.get_class)],
            3: [MessageHandler(filters.Document.FileExtension('pdf'), load_tt.load_pdf)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, load_tt.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, load_tt.timeout_func)]
        },
        fallbacks=[CommandHandler('end_load', load_tt.end_setting)],
        conversation_timeout=120
    )
    load_changes_in_tt_handler = ConversationHandler(
        entry_points=[CommandHandler('changes', load_changes_in_tt.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_changes_in_tt.get_pswrd)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_changes_in_tt.get_date)],
            3: [MessageHandler(filters.Document.FileExtension('pdf'), load_changes_in_tt.load_pdf)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, load_changes_in_tt.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, load_changes_in_tt.timeout_func)]
        },
        fallbacks=[CommandHandler('end_changes', load_changes_in_tt.end_setting)],
        conversation_timeout=120
    )
    config_extra = ConversationHandler(
        entry_points=[CommandHandler("extra", extra_lesson_dialog.start)],
        states={
            1: [CallbackQueryHandler(extra_lesson_dialog.yes_no)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, extra_lesson_dialog.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, extra_lesson_dialog.timeout_func)]},
        fallbacks=[CommandHandler('end_extra', extra_lesson_dialog.get_out)],
    conversation_timeout=30)

    sup = Support()
    prof = Profile()
    sup_hadler = CommandHandler('support', sup.get_supp)
    prof_handler = CommandHandler('profile', prof.get_profile)

    reset_cl = Reset_Class()
    giving_cl = GivePermissionToChangePsw()
    reset_handler = CommandHandler('reset', reset_cl.reset_admin_password)
    giving_conver = ConversationHandler(
        entry_points=[CommandHandler('give', giving_cl.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, giving_cl.get_username)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, giving_cl.get_confirmed)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, giving_cl.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, giving_cl.timeout_func)]
        },
        fallbacks=[CommandHandler('end_give', giving_cl.end_give)],
        conversation_timeout=120
    )

    taking_cl = TakePermissionToChangePsw()
    taking_conver = ConversationHandler(
        entry_points=[CommandHandler('take', taking_cl.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, taking_cl.get_username)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, taking_cl.get_confirmed)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, taking_cl.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, taking_cl.timeout_func)]
        },
        fallbacks=[CommandHandler('end_take', taking_cl.end_give)],
        conversation_timeout=120
    )

    timetable_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, timetable__.get_timetable)
    check_ = CheckStudentTT()
    checking_handler = ConversationHandler(
        entry_points=[CommandHandler('check', check_.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_day)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, check_.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, check_.timeout_func)]
        },
        fallbacks=[CommandHandler('end_check', check_.end_checking)],
        conversation_timeout=30
    )
    sticker_upload = GetSticker()
    stircker_conv = ConversationHandler(
        entry_points=[CommandHandler('sticker', sticker_upload.start)],
        states={
            1: [MessageHandler(filters.Sticker.ALL, sticker_upload.get_sticker)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, sticker_upload.timeout_func)],
            ConversationHandler.END: [TypeHandler(Update, sticker_upload.timeout_func)]
        },
        fallbacks=[CommandHandler('end_sticker', sticker_upload.end_uploading)],
        conversation_timeout=30
    )

    get_info_handler = CommandHandler('info', reset_cl.get_info_about_bot)

    game__ = GameMillioner()
    game_handler = CommandHandler('game', game__.send_poll)

    wolfram_ex = WolframClient()
    wolfram_handler = ConversationHandler(
        entry_points=[CommandHandler('wolfram', wolfram_ex.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, wolfram_ex.send_response)],
            ConversationHandler.END: [TypeHandler(Update, wolfram_ex.timeout_func)],
            ConversationHandler.TIMEOUT: [TypeHandler(Update, wolfram_ex.timeout_func)]
        },
        fallbacks=[CommandHandler('end_wolfram', wolfram_ex.end)],
        conversation_timeout=90
    )
    # !!!!
    load_extra = Load_Extra_Table()
    load_extra_handler = ConversationHandler(
        entry_points=[CommandHandler('extra_load', load_extra.start)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_extra.get_pswrd)],
                2: [MessageHandler(filters.Document.FileExtension('xlsx'), load_extra.load_pdf)],
                ConversationHandler.TIMEOUT: [TypeHandler(Update, load_extra.timeout_func)],
                ConversationHandler.END: [TypeHandler(Update, load_extra.timeout_func)]},
        fallbacks=[CommandHandler('end_extra_load', load_extra.end_setting)],
        conversation_timeout=120
    )

    exams_loader = LoadHTMLExams()
    exams_loader_handler = ConversationHandler(
        entry_points=[CommandHandler('exams_load', exams_loader.start)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, exams_loader.get_pswrd)],
                2: [MessageHandler(filters.Document.FileExtension('html'), exams_loader.load_html)],
                ConversationHandler.TIMEOUT: [TypeHandler(Update, exams_loader.timeout_func)],
                ConversationHandler.END: [TypeHandler(Update, exams_loader.timeout_func)]},
        fallbacks=[CommandHandler('end_exams_load', exams_loader.end_setting)],
        conversation_timeout=120
    )

    exams_checker = CheckClassExam()
    exams_checker_handler = ConversationHandler(
        entry_points=[CommandHandler('exams', exams_checker.start)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, exams_checker.get_month)],
                2: [MessageHandler(filters.TEXT & ~filters.COMMAND, exams_checker.get_class)],
                ConversationHandler.TIMEOUT: [TypeHandler(Update, exams_checker.timeout_func)],
                ConversationHandler.END: [TypeHandler(Update, exams_checker.timeout_func)]},
        fallbacks=[CommandHandler('end_exams', exams_checker.end_setting)],
        conversation_timeout=60
    )

    application.add_handlers(handlers={1: [conv_handler], 2: [timetable_handler], 3: [edit_user_handler],
                                       4: [mailto_handler], 5: [load_tt_handler], 6: [prof_handler],
                                       7: [sup_hadler], 8: [load_changes_in_tt_handler], 9: [config_extra],
                                       10: [checking_handler], 11: [stircker_conv],
                                       12: [MessageHandler(filters.Sticker.ALL, sticker_upload.send_random_sticker)],
                                       13: [CommandHandler('erase_all', sticker_upload.erase_all)],
                                       14: [reset_handler], 15: [giving_conver], 16: [get_info_handler],
                                       17: [taking_conver], 18: [load_extra_handler],
                                       19: [wolfram_handler], 20: [game_handler],
                                       21: [PollAnswerHandler(game__.get_answer)],
                                       22: [CommandHandler('stats', reset_cl.get_statistics)],
                                       23: [exams_loader_handler], 24: [exams_checker_handler]})
    asyncio.gather(application.bot.set_webhook('', max_connections=100))
    # drop_pending_updates=True
    application.run_polling()


if __name__ == '__main__':
    db_session.global_init("database/telegram_bot.db")
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action="store_true", help="The flag which says to update timetables or not.")
    args = parser.parse_args()
    main(do_update=args.update)
