from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from nexus import VERSION
from nexus.config import TOKEN, LOG
from nexus.store import init_db
from nexus.handlers import start, help_cmd, myid, info, admin, mode_cmd, allow_cmd, remove_cmd, users_cmd, text_handler, media_handler, callbacks, error_handler

def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN is missing; configure it in hosting environment variables")
    init_db()
    app=Application.builder().token(TOKEN).concurrent_updates(8).build()
    for name,fn in [("start",start),("help",help_cmd),("id",myid),("admin",admin),("mode",mode_cmd),("allow",allow_cmd),("remove",remove_cmd),("users",users_cmd)]: app.add_handler(CommandHandler(name,fn))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    app.add_handler(MessageHandler(filters.PHOTO|filters.VIDEO|filters.Document.ALL|filters.AUDIO|filters.VOICE,media_handler))
    app.add_error_handler(error_handler)
    LOG.info("NEXUS V%s starting",VERSION); app.run_polling()
if __name__=="__main__": main()
