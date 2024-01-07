import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from py_scripts.class_timetable import *
from py_scripts.class_edit_user import *
from py_scripts.class_mailing import *
from py_scripts.class_start import *
from py_scripts.class_load_timetable import *
from py_scripts.classes_support_profile import *
from py_scripts.class_extra_lesson import *
from py_scripts.class_get_diff_timetable import *
from py_scripts.stickers_class import *


try:
    if not os.path.exists('out/'):
        os.mkdir("out/")
    if not os.path.exists('changes_tt/'):
        os.mkdir("changes_tt/")
    if not os.path.exists('timetables/'):
        os.mkdir("timetables/")
    if not os.path.exists('timetables_csv/'):
        os.mkdir("timetables_csv/")
except Exception:
    pass


logging.basicConfig(
    filename='out/logs.log', filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)
logger = logging.getLogger(__name__)


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    start_dialog = SetTimetable()
    timetable__ = GetTimetable()
    edit_user_class = Edit_User()
    mail_dialog = MailTo()
    load_tt = LoadTimetables()
    load_changes_in_tt = LoadEditsTT()
    extra_lesson_dialog = Extra_Lessons()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_psw)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_third_name)]
        },
        fallbacks=[CommandHandler('end', start_dialog.end_setting)]
    )
    edit_user_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', edit_user_class.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_psw)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_class.get_third_name)]
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
            5: [MessageHandler(filters.Document.ALL, mail_dialog.get_attachments),
                MessageHandler(filters.TEXT & ~filters.COMMAND, mail_dialog.get_ready),
                MessageHandler(filters.AUDIO, mail_dialog.get_attachments)]
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
    load_changes_in_tt_handler = ConversationHandler(
        entry_points=[CommandHandler('changes', load_changes_in_tt.start)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_changes_in_tt.get_pswrd)],
                2: [MessageHandler(filters.TEXT & ~filters.COMMAND, load_changes_in_tt.get_date)],
                3: [MessageHandler(filters.Document.FileExtension('pdf'), load_changes_in_tt.load_pdf)]},
        fallbacks=[CommandHandler('end_changes', load_changes_in_tt.end_setting)]
    )
    config_extra = ConversationHandler(
        entry_points=[CommandHandler("extra", extra_lesson_dialog.start)],
        states={
            1: [CallbackQueryHandler(extra_lesson_dialog.yes_no)]},
        fallbacks=[CommandHandler('end_extra', extra_lesson_dialog.get_out)], )

    sup = Support()
    prof = Profile()
    sup_hadler = CommandHandler('support', sup.get_supp)
    prof_handler = CommandHandler('profile', prof.get_profile)
    timetable_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, timetable__.get_timetable)
    check_ = CheckStudentTT()
    checking_handler = ConversationHandler(
        entry_points=[CommandHandler('check', check_.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_name)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_.get_day)]
        },
        fallbacks=[CommandHandler('end_check', check_.end_checking)]
    )
    sticker_upload = GetSticker()
    stircker_conv = ConversationHandler(
        entry_points=[CommandHandler('new_sticker', sticker_upload.start)],
        states={
            1: [MessageHandler(filters.Sticker.ALL, sticker_upload.get_sticker)]
        },
        fallbacks=[CommandHandler('stick_end', sticker_upload.end_uploading)]
    )
    application.add_handlers(handlers={1: [conv_handler], 2: [timetable_handler], 3: [edit_user_handler],
                                       4: [mailto_handler], 5: [load_tt_handler], 6: [prof_handler],
                                       7: [sup_hadler], 8: [load_changes_in_tt_handler], 9: [config_extra],
                                       10: [checking_handler], 11: [stircker_conv],
                                       12: [MessageHandler(filters.Sticker.ALL, sticker_upload.send_random_sticker)],
                                       13: [CommandHandler('erase_all', sticker_upload.erase_all)]})
    application.run_polling()


if __name__ == '__main__':
    main()
    db_sess.close()
