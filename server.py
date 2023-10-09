import asyncio
import logging
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from config import BOT_TOKEN
from class_start import *
from class_timetable import *


logging.basicConfig(
    filename='out/logs.log', filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start', 'Начать настройку данных')])


def main():
    try:
        if not os.path.exists('out/'):
            os.mkdir("out/")
    except Exception:
        pass

    asyncio.run(write_all(bot))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(BOT_TOKEN).build()
    # .post_init(post_init)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    start_dialog = SetTimetable()
    timetable__ = GetTimetable()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_dialog.start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_class)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_familia)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_dialog.get_name)]
        },
        fallbacks=[CommandHandler('end', start_dialog.end_setting)]
    )
    timetable_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, timetable__.get_timetable)
    application.add_handlers(handlers={1: [conv_handler], 2: [timetable_handler]})
    application.run_polling()


if __name__ == '__main__':
    db_session.global_init("database/telegram_bot.db")
    main()
