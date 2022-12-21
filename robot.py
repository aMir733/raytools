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

YES, NO = "✅", "❌"
MENU, EDIT = range(2)
REVOKE, RENEW = range(2)
COUNT, DATE, UUID, STATUS, DONE, CANCEL = range(6)
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
    "revoked": "✅آی دی تغییر یافت",
    "cancel": "لغو❌",
    "canceled": "لغو شد.",
    "canceled_noneed": "شما در حین عملیاتی نیستید.",
    "revoke": "تغییر آی دی",
    "renew": "تغییر تاریخ",
    "enable": "فعال",
    "disable": "غیر فعال",
    "enabled": "✅فعال شد",
    "disabled": "❌غیر فعال شد",
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
    "warning_invalidusername": "هشدار! شماره تماس وارد شده درست نمیباشد. برای بازگشت از دکمه لغو استفاده کنید.",
    "menu_revoke": "تغییر یو یو آی دی",
    "for_user": "برای کاربری",
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
    if len(args) == 0:
        return None
    return True

def read_args(args):
    if isinstance(args, str):
        return args.split(SPLIT)[1:]
    return args

async def add_menu(update, context):
    if len(context.args) == 0:
        return ConversationHandler.END
    if not check_username(context.args[0]):
        await update.message.reply_text(MGS["warning_invalidusername"])
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
    query = update.callback_query
    if query:
        await query.answer()
    args = read_args(context.args or query.data)
    if len(args) == 0:
        return ConversationHandler.END
    if not check_username(args[0]):
        await update.message.reply_text(MGS["warning_invalidusername"])
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
    text = args[0]
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=reply_markup)
    return MENU

async def revoke_menu(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    args = read_args(context.args or query.data)
    if len(args) == 0:
        return ConversationHandler.END
    uuid = make_uuid()
    keyboard = [
        [
            InlineKeyboardButton(f"{MGS['uuid']}{SPLIT}{uuid}", callback_data=str(UUID))
        ],
        [
            InlineKeyboardButton(MGS["confirm"], callback_data=str(DONE)),
            InlineKeyboardButton(MGS["cancel"], callback_data=str(CANCEL))
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    #text = f"{MGS['menu_revoke']}{MGS['for_user']}: {args[0]}"
    text = args[0]
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=reply_markup)
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

async def edit_revoke(update, context):
    query = update.callback_query
    args = query.data.split(SPLIT)
    context.user_data["query"] = args
    await query.answer()
    try:
        username = args[1]
    except IndexError:
        return ConversationHandler.END
    await context.bot.send_message(update.effective_chat.id, MGS["reply_uuid"])
    return EDIT

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

async def cancel_noneed(update, context):
    await context.bot.send_message(update.effective_chat.id, MGS["canceled_noneed"])
    
async def add(update, context):
    if not (update.message or update.callback_query).from_user.id in ADMINS_RW:
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    message = query.message
    res = read_keyboard(message.reply_markup.inline_keyboard)
    username = message.text
    count = res[str(COUNT)].split(SPLIT)[1]
    uuid = res[str(UUID)].split(SPLIT)[1]
    date = get_date(res[str(DATE)].split(SPLIT)[1])
    if not check_username(username):
        await context.bot.send_message(update.effective_chat.id, MGS["warning_invalidusername"])
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
    await message.delete()
    return ConversationHandler.END

async def renew(update, context):
    if not (update.message or update.callback_query).from_user.id in ADMINS_RW:
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    message = query.message
    res = read_keyboard(message.reply_markup.inline_keyboard)
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
    text = f"{MGS['renewed']}\n{MGS['user']} `{username}`\n{MGS['date']}: {time_str}"
    await context.bot.send_message(update.effective_chat.id, esc_markdown(text), parse_mode="MarkdownV2")
    await message.delete()
    return ConversationHandler.END

async def revoke(update, context):
    if not (update.message or update.callback_query).from_user.id in ADMINS_RW:
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    message = query.message
    username = message.text
    res = read_keyboard(message.reply_markup.inline_keyboard)
    uuid = res[str(UUID)].split(SPLIT)[1]
    if not check_uuid(uuid):
        await context.bot.send_message(update.effective_chat.id, MGS["invalid_uuid"] + f": {uuid}")
        return ConversationHandler.END
    database = db.session()
    err = None
    try:
        handle_revoke(database, user=username, uuid=uuid)
    except NoResultFound:
        err = f"{MGS['error']}: {MGS['user_notexists']}"
    except Exception as e:
        err = f"{MGS['error']}: {str(e)}"
    if err:
        await context.bot.send_message(update.effective_chat.id, err)
        await message.delete()
        return ConversationHandler.END
    text = f"{MGS['revoked']}\n{MGS['user']} `{username}`\n{MGS['uuid']}: `{uuid}`"
    await context.bot.send_message(update.effective_chat.id, esc_markdown(text), parse_mode="MarkdownV2")
    await message.delete()
    return ConversationHandler.END

async def get(update, context):
    if not (update.message or update.callback_query).from_user.id in ADMINS_RO:
        return ConversationHandler.END
    if len(context.args) == 0:
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
    username = user.username
    time_str = timetostr(stamptotime(user.expires))
    status = MGS['status_disabled'] if user.disabled else MGS['status_enabled']
    reason = f"{MGS.get('reason_' + str(user.disabled), str(user.disabled))}" if user.disabled else ""
    text = '\n'.join((f"{MGS['user']} `{username}`",
            ': '.join([status, reason]),
            f"{MGS['id']}: {str(user.id)}",
            f"{MGS['count']}: {str(user.count)}",
            f"{MGS['uuid']}: `{user.uuid}`",
            f"{MGS['traffic']}: {readable_size(user.traffic)}",
            f"{MGS['date']}: {time_str}",
            ))
    if user.disabled:
        f_row = [InlineKeyboardButton(MGS["enable"], callback_data=f"{str(STATUS)}{SPLIT}{username}{SPLIT}1")]
        l_row = []
    else:
        f_row = [InlineKeyboardButton(MGS["disable"], callback_data=f"{str(STATUS)}{SPLIT}{username}{SPLIT}0")]
        l_row = [InlineKeyboardButton(MGS["get_server"], url=f"https://t.me/{update.effective_chat.title}?start={user.uuid}")]
    keyboard = [
        f_row,
        [
            InlineKeyboardButton(MGS["revoke"], callback_data=f"{str(REVOKE)}{SPLIT}{username}{SPLIT}{user.uuid}"),
            InlineKeyboardButton(MGS["renew"], callback_data=f"{str(RENEW)}{SPLIT}{username}"),
        ],
        l_row,
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(esc_markdown(text), reply_markup=reply_markup, parse_mode="MarkdownV2")

async def status(update, context):
    query = update.callback_query
    if not (update.message or query).from_user.id in ADMINS_RW:
        return ConversationHandler.END
    if query:
        await query.answer()
    args = read_args(context.args or query.data)
    if len(args) > 2:
        return ConversationHandler.END
    message = query.message
    username = args[0]
    reason = ("unknown", None)[int(args[1])]
    database = db.session()
    err = None
    try:
        handle_disable(database, user=username, reason=reason)
    except NoResultFound:
        err = f"{MGS['error']}: {MGS['user_notexists']}"
    except Exception as e:
        err = f"{MGS['error']}: {str(e)}"
    if err:
        await context.bot.send_message(update.effective_chat.id, err)
        await message.delete()
        return ConversationHandler.END
    msg = MGS['disabled'] if reason else MGS['enabled']
    text = f"{msg}\n{MGS['user']} `{username}`"
    await context.bot.send_message(update.effective_chat.id, esc_markdown(text), parse_mode="MarkdownV2")
    await message.delete()
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
    global db
    db = Database(db_path)

    app = ApplicationBuilder().token(args.yaml["token"]).build()
    filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

    global CHAT, ADMINS_RO, ADMINS_RW
    CHAT = args.yaml["chat"]
    ADMINS_WRITE = args.yaml["admins"] if "admins" in args.yaml else []
    ADMINS_READ = args.yaml["admin_r"] if "admin_r" in args.yaml else []
    ADMINS_RO = {*ADMINS_READ, *ADMINS_WRITE}
    ADMINS_RW = {*ADMINS_WRITE}
    
    FILTER_CHAT = filters.Chat(CHAT)
    FILTER_ADMINS = filters.User(ADMINS_RW) if ADMINS_RW else filters.ALL
    FILTER_ADMINS_R = filters.User(ADMINS_RO) if ADMINS_RO else filters.ALL

    READ_WRITE = (FILTER_CHAT & FILTER_ADMINS)
    READ_ONLY = (FILTER_CHAT & FILTER_ADMINS_R)
    
    EDIT_COUNT = CallbackQueryHandler(edit_count, "^" + str(COUNT) + "$")
    EDIT_DATE = CallbackQueryHandler(edit_date, "^" + str(DATE) + "$")
    EDIT_UUID = CallbackQueryHandler(edit_uuid, "^" + str(UUID) + "$")
     
    EDIT_ENTRY = [MessageHandler(filters.TEXT, edit)]
    
    FALL_CANCELS = (
        CallbackQueryHandler(cancel, "^" + str(CANCEL) + "$"),
        CommandHandler("cancel", cancel)
        )

    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("add", add_menu, filters=READ_WRITE)],
            states={
                MENU: [
                    EDIT_COUNT,
                    EDIT_DATE,
                    EDIT_UUID,
                ],
                EDIT: EDIT_ENTRY
            },
            fallbacks=[
                CallbackQueryHandler(add, "^" + str(DONE) + "$"),
                *FALL_CANCELS
            ],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("revoke", revoke, filters=READ_WRITE), CallbackQueryHandler(revoke_menu, f"^{str(REVOKE)}{SPLIT}")],
            states={
                MENU: [
                    EDIT_UUID,
                ],
                EDIT: EDIT_ENTRY
            },
            fallbacks=[
                CallbackQueryHandler(revoke, "^" + str(DONE) + "$"),
                *FALL_CANCELS
            ],
        )
    )
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("renew", renew_menu, filters=READ_WRITE), CallbackQueryHandler(renew_menu, f"^{str(RENEW)}{SPLIT}")],
            states={
                MENU: [
                    EDIT_DATE,                    
                ],
                EDIT: EDIT_ENTRY
            },
            fallbacks=[
                CallbackQueryHandler(renew, "^" + str(DONE) + "$"),
                *FALL_CANCELS,
            ],
        )
    )
    app.add_handler(CommandHandler("get", get, filters=READ_ONLY))
    app.add_handler(CommandHandler("cancel", cancel_noneed, filters=(filters.ALL)))
    app.add_handler(CallbackQueryHandler(status, f"^{str(STATUS)}{SPLIT}"))

    app.run_polling()

if __name__ == "__main__":
    main()