from raytools.parser import Robot
from raytools.db import Database
from raytools.log import *
from raytools.func import *
from raytools.handle import *
from sqlalchemy.exc import *
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
SPLIT = ": "

MGS = {
    "user": "👤 کاربری",
    "count": "1️⃣ تعداد",
    "date": "🕓 تاریخ انقضا",
    "uuid": "🔐 آی دی",
    "traffic": "〽️ ترافیک مصرفی",
    "id": "🔢 آی دی عددی",
    "invalid": "نامعتبر",
    "error": "ارور",
    "confirm": "ثبت✅",
    "added": "ثبت شد✅",
    "renewed": "تمدید شد✅",
    "cancel": "لغو❌",
    "canceled": "لغو شد.",
    "invalid_user": "کاربری نامعتبر",
    "invalid_count": "تعداد نامعتبر",
    "invalid_date": "تاریخ نامعتبر",
    "invalid_uuid": "آی دی نامعتبر",
    "reply_count": "تعداد را ریپلای کنید.",
    "reply_date": "تاریخ را ریپلای کنید.",
    "reply_uuid": "آی دی را ریپلای کنید.",
    "count_one": "هشدار: لطفا برای هر یوزر و دستگاه یک آی دی وارد کنید.",
    "get_server": "دریافت سرور",
    "user_exists": "کاربری در سیستم ثبت شده",
    "user_notexists": "کاربری یافت نشد",
    "status_enabled": "✅ فعال",
    "status_disabled": "❌ غیر فعال",
    "reason_count": "تعداد بیش از حد",
    "reason_expired": "انقضا تاریخ",
}

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

def esc_markdown(text):
    return text.replace(".", "\.").replace("_", "\_").replace("-", "\-")

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
        await update.message.reply_text(MGS["invalid"])
        return ConversationHandler.END
    keyboard = [
            [
                InlineKeyboardButton(f"{MGS['count']}{SPLIT}1", callback_data=str(COUNT)),
                InlineKeyboardButton(f"{MGS['date']}{SPLIT}+30", callback_data=str(DATE)),
            ],
            [
                InlineKeyboardButton(f"{MGS['uuid']}{SPLIT}{make_uuid()}", callback_data=str(UUID)),
            ],
            [
                InlineKeyboardButton(MGS["confirm"], callback_data=str(DONE)),
                InlineKeyboardButton(MGS["cancel"], callback_data=str(CANCEL))
            ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(context.args[0], reply_markup=reply_markup)
    return MENU

async def renew_menu(update, context):
    if not check_args(context.args):
        await update.message.reply_text(MGS["invalid"])
        return ConversationHandler.END
    keyboard = [
        [
            InlineKeyboardButton(f"{MGS['date']}{SPLIT}+30", callback_data=str(DATE))
        ],
        [
                InlineKeyboardButton(MGS["confirm"], callback_data=str(DONE)),
                InlineKeyboardButton(MGS["cancel"], callback_data=str(CANCEL))
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(context.args[0], reply_markup=reply_markup)
    return MENU

async def edit(update, context):
    query = context.user_data["query"]
    res = read_keyboard(query.message.reply_markup.inline_keyboard)
    text = f"{res[query.data].split(SPLIT)[0]}{SPLIT}{update.message.text}"
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
    await context.bot.send_message(update.effective_chat.id, MGS["count_one"])
    await context.bot.send_message(update.effective_chat.id, MGS["reply_count"])
    return EDIT

async def edit_date(update, context):
    query = update.callback_query
    context.user_data["query"] = query
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, MGS["reply_date"])
    return EDIT

async def edit_uuid(update, context):
    query = update.callback_query
    context.user_data["query"] = query
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, MGS["reply_uuid"])
    return EDIT

async def cancel(update, context):
    try:
        query = update.callback_query
        await query.answer()
        await query.delete_message()
    except:
        pass
    await context.bot.send_message(update.effective_chat.id, MGS["canceled"])
    return ConversationHandler.END
    
async def add(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    res = read_keyboard(message.reply_markup.inline_keyboard)
    username = message.text
    count = res[str(COUNT)].split(SPLIT)[1]
    uuid = res[str(UUID)].split(SPLIT)[1]
    date = get_date(res[str(DATE)].split(SPLIT)[1])
    if not check_username(username):
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_user"] + f": {count}")
        return ConversationHandler.END
    if not check_count(count):
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_count"] + f": {count}")
        return ConversationHandler.END
    if not check_uuid(uuid):
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_uuid"] + f": {uuid}")
        return ConversationHandler.END
    if not date:
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_date"] + f": {date}")
        return ConversationHandler.END
    database = db.session()
    err = None
    try:
        handle_add(database, username=username, count=count, expires=date, uuid=uuid)
    except IntegrityError:
        err = f"{MGS['error']}: {MGS['user_exists']}"
    except Exception as e:
        err = f"{MGS['error']}: {str(e)}"
    if err:
        await context.bot.send_message(update.effective_chat.id, err)
        await message.delete()
        return ConversationHandler.END
    time_str = timetostr(stamptotime(date))
    text = f"{MGS['added']}\n{MGS['user']} `{username}`\n{MGS['count']}: {count}\n{MGS['uuid']}: `{uuid}`\n{MGS['date']}: {time_str}"
    title = update.effective_chat.title
    keyboard = [[InlineKeyboardButton(MGS["get_server"], url=f"https://t.me/{title}?start={uuid}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(update.effective_chat.id, esc_markdown(text), reply_markup=reply_markup, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def renew(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    res = read_keyboard(message.reply_markup.inlinke_keyboard)
    username = message.text
    date = get_date(res[str(DATE)].split(SPLIT)[1])
    if not check_username(username):
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_user"] + f": {count}")
        return ConversationHandler.END
    if not date:
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_date"] + f": {date}")
        return ConversationHandler.END
    database = db.session()
    err = None
    try:
        handle_renew(database, user=username, expires=date)
    except NoResultFound:
        err = f"{MGS['error']}: {MGS['user_notexists']}"
    except Exception as e:
        err = f"{MGS['error']}: {str(e)}"
    if err:
        await context.bot.send_message(update.effective_chat.id, err)
        await message.delete()
        return ConversationHandler.END
    time_str = timetostr(stamptotime(date))
    text = f"{MGS['renewd']}\n{MGS['user']} `{username}`\n{MGS['date']}: {time_str}"
    await context.bot.send_message(update.effective_chat.id, esc_markdown(text), parse_mode="MarkdownV2")
    return ConversationHandler.END

async def get(update, context):
    if not check_args(context.args):
        await update.message.reply_text(MGS["invalid"])
        return
    username = context.args[0]
    database = db.session()
    err = None
    try:
        user = handle_get(database, user=username)
    except NoResultFound:
        err = f"{MGS['error']}: {MGS['user_notexists']}"
    except Exception as e:
        err = f"{MGS['error']}: {str(e)}"
    if err:
        await context.bot.send_message(update.effective_chat.id, err)
        return
    status = MGS['status_enabled'] if not user.disabled else f"{MGS['status_disabled']}: {MGS.get('reason_' + str(user.disabled), str(user.disabled))}"
    time_str = timetostr(stamptotime(user.expires))
    text = '\n'.join((f"{MGS['user']} `{username}`",
            f"{status}",
            f"{MGS['id']}: {str(user.id)}",
            f"{MGS['count']}: {str(user.count)}",
            f"{MGS['uuid']}: `{user.uuid}`",
            f"{MGS['traffic']}: {readable_size(user.traffic)}",
            f"{MGS['date']}: {time_str}",
            ))

    await update.message.reply_text(esc_markdown(text), parse_mode="MarkdownV2")

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
    global db
    db = Database(db_path)

    app = ApplicationBuilder().token(args.yaml["token"]).build()
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
    
    EDIT_COUNT = CallbackQueryHandler(edit_count, "^" + str(COUNT) + "$")
    EDIT_DATE = CallbackQueryHandler(edit_date, "^" + str(DATE) + "$")
    EDIT_UUID = CallbackQueryHandler(edit_uuid, "^" + str(UUID) + "$")
    
    FALL_CANCEL = CallbackQueryHandler(cancel, "^" + str(CANCEL) + "$")
    
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
                FALL_CANCEL,
            ],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("renew", renew_menu, filters=(ADMIN_CHAT))],
            states={
                MENU: [
                    EDIT_DATE,                    
                ],
                EDIT: [
                    MessageHandler(filters.TEXT, edit)
                ],
            },
            fallbacks=[
                CallbackQueryHandler(renew, "^" + str(DONE) + "$"),
                FALL_CANCEL,
            ],
        )
    )
    app.add_handler(CommandHandler("get", get, filters=(ADMIN_CHAT)))

    app.run_polling()

if __name__ == "__main__":
    main()