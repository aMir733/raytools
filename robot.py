from raytools.parser import Robot
from raytools.db import Database
from raytools.log import *
from raytools.func import *
from raytools.handle import *
import re
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)


MENU, EDIT = range(2)
COUNT, DATE, UUID, DONE, CANCEL = range(5)

def replace_keyboard(keyboard, callback_data, replace):
    final = []
    for i in keyboard:
        if isinstance(i, (list, tuple)):
            final.append(replace_keyboard(i, callback_data, replace))
            continue
        if i.callback_data == callback_data:
            final.append(replace)
            continue
        final.append(i)
    return final
                
def read_keyboard(keyboard):
    final = {}
    for i in keyboard:
        if isinstance(i, (list, tuple)):
            final = {**read_keyboard(i), **final}
            continue
        final[i.callback_data] = i.text
    return final

def check_username(username):
    return re.match(r"^[0-9]{11}(\-[0-9]+)?$", username)

def check_uuid(uuid):
    return isuuid(uuid)

def get_date(date):
    try:
        return parse_date(date)
    except:
        pass

def check_count(count):
    return count.isdigit()

def check_args(args):
    if len(args) == 0 or not check_username(args[0]):
        return None
    return True

async def add_menu(update, context):
    if not check_args(context.args):
        await update.message.reply_text("نامعتبر")
        return ConversationHandler.END
    keyboard = [
            [
                InlineKeyboardButton("1", callback_data=str(COUNT)),
                InlineKeyboardButton("+30", callback_data=str(DATE)),
            ],
            [
                InlineKeyboardButton(make_uuid(), callback_data=str(UUID)),
            ],
            [
                InlineKeyboardButton("ثبت✅", callback_data=str(DONE)),
                InlineKeyboardButton("لغو❌", callback_data=str(CANCEL))
            ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(context.args[0], reply_markup=reply_markup)
    return MENU

async def renew_menu(update, context):
    if not check_args(context.args):
        await update.message.reply_text("نامعتبر")
        return ConversationHandler.END
    keyboard = [
        [
            InlineKeyboardButton("+30", callback_data=str(DATE))
        ],
        [
                InlineKeyboardButton("ثبت✅", callback_data=str(DONE)),
                InlineKeyboardButton("لغو❌", callback_data=str(CANCEL))
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(context.args[0], reply_markup=reply_markup)
    return MENU

async def edit(update, context):
    text = update.message.text
    query = context.user_data["query"]
    message = query.message
    keyboard = message.reply_markup.inline_keyboard
    keyboard = replace_keyboard(keyboard, query.data, InlineKeyboardButton(text=text, callback_data=query.data))
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(update.effective_chat.id, message.text, reply_markup=reply_markup)
    await message.delete()
    return MENU

async def edit_count(update, context):
    query = update.callback_query
    context.user_data["query"] = query
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, "هشدار . لطفا تعداد را تغییر ندهید. هر یو یو ای وارد یک گوشی باید شود")
    await context.bot.send_message(update.effective_chat.id, "لطفا تعداد را ریپلای کنید")
    return EDIT

async def edit_date(update, context):
    query = update.callback_query
    context.user_data["query"] = query
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, "تاریخ را ریپلای کنید")
    return EDIT

async def edit_uuid(update, context):
    query = update.callback_query
    context.user_data["query"] = query
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, "یو یو ای دی را ریپلای کنید")
    return EDIT

async def cancel(update, context):
    try:
        query = update.callback_query
        await query.answer()
        await query.delete_message()
    except:
        pass
    await context.bot.send_message(update.effective_chat.id, "لغو شد")
    return ConversationHandler.END
    
async def add(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    res = read_keyboard(message.reply_markup.inline_keyboard)
    username = message.text
    count = res[str(COUNT)]
    uuid = res[str(UUID)]
    date = res[str(DATE)]
    try:
        handle_add(database, username=username, count=count, expires=expires, uuid=uuid)
    except:
        await context.bot.send_message(update.effective_chat.id, "ارور")
        await message.delete()
        return ConversationHandler.END
    text = f"ثبت شد ✅\n کاربر `{username}`\nتعداد: {count}\nیو یو آی دی: `{uuid}`\nانقضا: {date} ({expires})"
    title = update.effective_chat.title
    keyboard = [[InlineKeyboardButton("دریافت سرور", url=f"https://t.me/{title}?start={uuid}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

def main():
    parser = Robot()
    args = parser.parse()
    configure_logging(
        logging,
        level=10,
        format="%(asctime)s (%(name)s): %(message)s",
        filename=args.output_log,
        )
    for i in ["chat", "token"]:
        if i not in args.yaml:
            raise KeyError(f"No {i} found in your yaml file")

    db_path = args.__dict__.pop('database')
    db = Database(db_path)
    global database
    database = db.session()

    app = ApplicationBuilder().token(args.yaml["token"]).build()
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
    
    EDIT_COUNT = CallbackQueryHandler(edit_count, "^" + str(COUNT) + "$"),
    EDIT_DATE = CallbackQueryHandler(edit_date, "^" + str(DATE) + "$"),
    EDIT_UUID = CallbackQueryHandler(edit_uuid, "^" + str(UUID) + "$"),
    
    ADMIN_CHAT = filters.Chat(args.yaml["chat"])
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("add", add_menu, filters=(ADMIN_CHAT))],
            states={
                MENU: [
                    EDIT_COUNT,
                    EDIT_DATE,
                    EDIT_UUID,
                ],
                EDIT: [
                    MessageHandler(filters.TEXT, edit)
                ],
            },
            fallbacks=[
                CallbackQueryHandler(add, "^" + str(DONE) + "$"),
                CallbackQueryHandler(cancel, "^" + str(CANCEL) + "$"),
            ],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("renew", renew_menu, filters=(ADMIN_CHAT))],
            state={
                MENU: [
                    EDIT_DATE,                    
                ]
                EDIT: [
                    MessageHandler(filters.TEXT, edit)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(renew, "^" + str(DONE) + "$"),
                CallbackQueryHandler(cancel, "^" + str(CANCEL) + "$"),
            ],
        )
    )

    app.run_polling()

if __name__ == "__main__":
    main()