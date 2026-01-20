import json
from pathlib import Path

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ================== تنظیمات اصلی ==================

TOKEN = "8230609347:AAFPXn0edGPijh4FGpLoaYyiRNPRMzfiV6U"     # توکن بات
ADMIN_CHAT_ID = -1003187011081       # chat_id عددی ادمین

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "reservations.json"  # ذخیره کنار bot.py

# فایل/عکس برای گزینه «عکس‌ها» (بگذار کنار bot.py)
PHOTOS_FILE_PATH = BASE_DIR / "room.zip"  # این اسم رو با فایل خودت عوض کن

# متن برای گزینه «آدرس»
ADDRESS_TEXT = (
    "آدرس ما:\n"
    "مسقط.عذیبه.پشت المیره و ریال سنتر\n"
)

# کدهای مخفی
SECRET_LOCATION_CODE = "loc123"   # هر کدی دوست داری بگذار
SECRET_WIFI_CODE = "wifi123"      # هر کدی دوست داری بگذار

# مختصات لوکیشن (مثال: تهران)
LOCATION_LAT = 23.594297
LOCATION_LON = 58.376367

# متن رمز وای‌فای
WIFI_PASSWORD_TEXT = (
    "نام وای‌فای: TP-Link_5179_5G and Tp-Link_topfloorq\n"
    "رمز: 1361649093"
)
# ================== استیت‌های گفتگو ==================

ASK_PHONE, ASK_PEOPLE, ASK_NIGHTS, ASK_DATE, ASK_ALT_CONTACT, ASK_FULLNAME = range(6)

# ================== متن دکمه‌ها ==================

BACK_BUTTON = "⬅️ مرحله قبل"
CANCEL_BUTTON = "لغو درخواست ❌"
CONTACT_BUTTON = "ارسال شماره من"

PHOTOS_BUTTON = "📷 عکس‌ها"
ADDRESS_BUTTON = "📍 آدرس"
poshtbani_button = "🆘 پشتیبانی"

tozehat_button = "تضیحات در مورد هاستل  ما ℹ️"


# ================== توابع کمکی JSON و خلاصه ==================

def save_reservation_to_json(reservation: dict):
    """ذخیره یک رزرو در فایل JSON (به صورت لیست)."""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    data.append(reservation)

    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_reservation_record(user, user_data: dict, status: str) -> dict:
    """ساخت یک رکورد رزرو از اطلاعات فعلی کاربر + وضعیت (submitted/canceled)."""
    return {
        "status": status,  # submitted یا canceled
        "telegram_id": user.id,
        "telegram_username": user.username,
        "fullname": user_data.get("fullname"),
        "phone": user_data.get("phone"),
        "people": user_data.get("people"),
        "nights": user_data.get("nights"),
        "date": user_data.get("date"),
        "alt_contact": user_data.get("alt_contact"),
    }


def build_summary_text(reservation: dict, canceled: bool = False) -> str:
    """ساخت متن خلاصه برای ارسال به ادمین."""
    header = "یک درخواست رزرو لغو شد ❌" if canceled else "درخواست رزرو جدید ✅"
    lines = [header, "----------------------"]

    if reservation.get("fullname"):
        lines.append(f"نام و نام خانوادگی: {reservation['fullname']}")
    if reservation.get("phone"):
        lines.append(f"شماره تلفن: {reservation['phone']}")
    if reservation.get("people"):
        lines.append(f"تعداد نفرات: {reservation['people']}")
    if reservation.get("nights"):
        lines.append(f"تعداد شب: {reservation['nights']}")
    if reservation.get("date"):
        lines.append(f"تاریخ ورود: {reservation['date']}")
    if reservation.get("alt_contact"):
        lines.append(f"راه ارتباطی مطمئن: {reservation['alt_contact']}")

    lines.append("----------------------")

    if reservation.get("telegram_username"):
        lines.append(f"telegram username: @{reservation['telegram_username']}")
    lines.append(f"telegram id: {reservation.get('telegram_id')}")

    lines.append(f"وضعیت: {reservation.get('status')}")

    return "\n".join(lines)


# ================== ارسال عکس، آدرس، لوکیشن، وای‌فای ==================

async def send_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال فایل/عکس برای گزینه «عکس‌ها»."""
    chat_id = update.effective_chat.id

    if not PHOTOS_FILE_PATH.exists():
        await context.bot.send_message(
            chat_id=chat_id,
            text="فایل عکس‌ها پیدا نشد. لطفاً بعداً دوباره امتحان کنید."
        )
        return

    suffix = PHOTOS_FILE_PATH.suffix.lower()
    with PHOTOS_FILE_PATH.open("rb") as f:
        if suffix in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            await context.bot.send_photo(chat_id=chat_id, photo=f)
        else:
            await context.bot.send_document(chat_id=chat_id, document=f)


async def send_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ADDRESS_TEXT)


async def send_location_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_location(
        chat_id=chat_id,
        latitude=LOCATION_LAT,
        longitude=LOCATION_LON
    )


async def send_wifi_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WIFI_PASSWORD_TEXT)


# ================== کیبوردها و سوال هر استیت ==================

def default_keyboard(include_contact: bool = False) -> ReplyKeyboardMarkup:
    """کیبورد پیش‌فرض: عکس‌ها / آدرس + برگشت / لغو + در صورت نیاز دکمه ارسال شماره."""
    buttons = []

    if include_contact:
        buttons.append([KeyboardButton(CONTACT_BUTTON, request_contact=True)])

    buttons.append([KeyboardButton(PHOTOS_BUTTON), KeyboardButton(ADDRESS_BUTTON)])
    buttons.append([KeyboardButton(BACK_BUTTON), KeyboardButton(CANCEL_BUTTON)])
    buttons.append([KeyboardButton(poshtbani_button)])
    buttons.append([KeyboardButton(tozehat_button)])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)


async def ask_phone_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام، خوش آمدید.\n"
        "برای ثبت درخواست رزرو، لطفاً شماره تلفن خود را ارسال کنید "
        "یا از دکمه «ارسال شماره من» استفاده کنید."
    )
    await update.message.reply_text(
        text,
        reply_markup=default_keyboard(include_contact=True)
    )


async def ask_people_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "چند نفر  هستید",
        reply_markup=default_keyboard()
    )


async def ask_nights_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تغییر: اطلاع حداقل 3 شب
    await update.message.reply_text(
        "برای چند شب اتاق می‌خواید؟ (حداقل 3 شب)",
        reply_markup=default_keyboard()
    )


async def ask_date_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "از چه تاریخی می‌خواید تشریف بیارید؟\n"
        "مثلاً: 1403/10/15 یا 2025-01-05",
        reply_markup=default_keyboard()
    )


async def ask_alt_contact_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "یک راه ارتباطی که همیشه پاسخگو هستید ارسال کنید.\n"
        "مثلاً: همین شماره، شماره واتساپ دیگر، آیدی اینستاگرام، تلگرام و ...",
        reply_markup=default_keyboard()
    )


async def ask_fullname_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "لطفاً نام و یا نام خانوادگی خود را برای ارتباط بهتر بنویسید.",
        reply_markup=default_keyboard()
    )


async def ask_question_for_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: int):
    """باتوجه به استیت، سوال مناسب را دوباره می‌پرسد (برای برگشت و بعد از عکس/آدرس)."""
    if state == ASK_PHONE:
        await ask_phone_question(update, context)
    elif state == ASK_PEOPLE:
        await ask_people_question(update, context)
    elif state == ASK_NIGHTS:
        await ask_nights_question(update, context)
    elif state == ASK_DATE:
        await ask_date_question(update, context)
    elif state == ASK_ALT_CONTACT:
        await ask_alt_contact_question(update, context)
    elif state == ASK_FULLNAME:
        await ask_fullname_question(update, context)


# ================== هندل مشترک دکمه‌ها + کدهای مخفی ==================

async def handle_special_inputs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    current_state: int
):
    """
    در هر مرحله، اگر کاربر یکی از موارد زیر را بزند:
    - عکس‌ها
    - آدرس
    - برگشت
    - لغو
    - کد مخفی لوکیشن
    - کد مخفی وای‌فای
    اینجا هندل می‌شود.
    """
    from telegram.ext import ConversationHandler

    text = (update.message.text or "").strip()

    # دکمه عکس‌ها
    if text == PHOTOS_BUTTON:
        await send_photos(update, context)
        await ask_question_for_state(update, context, current_state)
        return current_state
    

    if text == tozehat_button:
        await update.message.reply_text('''هاستل ما دارای اتاق های تمیز و مرتب با امکانات کامل می باشد. 
                                        فضای هاستل ما کاملا خوانوادگی هست  و فرد مجرد در ساختمان نداریم
                                        محیطی ارام و با ارامش بی سر و صدا   امکانات اتاقت کا کامل و فول هست   
                                        اشپز خانه  فول به همراه تمامی امکانت مورد نیاز دیگه 
                                        3 عدد وای فای در ساختمات  قرار داده شده برای سرعت و قدرت بیشتر که از فناوری  اینترنت  فایو جی  استفاده میشه
                                        اتاق ها قابلیت اضافه کردن تا  3_4 تخت رو دارد \n\n'''
        )
        await ask_question_for_state(update, context, current_state)
        return current_state

    # دکمه آدرس
    if text == ADDRESS_BUTTON:
        await send_address(update, context)
        await ask_question_for_state(update, context, current_state)
        return current_state

    # کد مخفی لوکیشن
    if text == SECRET_LOCATION_CODE:
        await send_location_secret(update, context)
        await ask_question_for_state(update, context, current_state)
        return current_state

    # کد مخفی وای‌فای
    if text == SECRET_WIFI_CODE:
        await send_wifi_secret(update, context)
        await ask_question_for_state(update, context, current_state)
        return current_state

    # لغو
    if text == CANCEL_BUTTON:
        await cancel(update, context)
        return ConversationHandler.END
    
    if text == poshtbani_button:
        await update.message.reply_text(
            "برای پشتیبانی با شماره زیر تماس بگیرید یا به ایدی های زیر پیام دهید \n"
            "+98 9030449865 (فقط پیام واتساپ) \n"
            "+968 99830910 (تماس در عمان و  پیام واتساپ)\n"
            "\n @Mamad_NOX_YT (تلگرام)\n @maha_mst40 (تلگرام )"
        )
        await ask_question_for_state(update, context, current_state)
        return current_state 

    # برگشت
    if text == BACK_BUTTON:
        # اگر اولین مرحله است، جایی برای برگشت نیست
        if current_state == ASK_PHONE:
            await update.message.reply_text("شما در اولین مرحله هستید و امکان برگشت وجود ندارد.")
            await ask_phone_question(update, context)
            return ASK_PHONE

        # تعیین استیت قبلی
        if current_state == ASK_PEOPLE:
            prev_state = ASK_PHONE
        elif current_state == ASK_NIGHTS:
            prev_state = ASK_PEOPLE
        elif current_state == ASK_DATE:
            prev_state = ASK_NIGHTS
        elif current_state == ASK_ALT_CONTACT:
            prev_state = ASK_DATE
        elif current_state == ASK_FULLNAME:
            prev_state = ASK_ALT_CONTACT    
        else:
            prev_state = ASK_PHONE

        await ask_question_for_state(update, context, prev_state)
        return prev_state

    # نه دکمه بود نه کد مخفی
    return None


# ================== هندلرهای گفتگو ==================

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # شروع فرم جدید
    await ask_phone_question(update, context)
    return ASK_PHONE


# گرفتن شماره تلفن
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # اگر contact فرستاده شده
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        # متن → ممکن است دکمه‌ها یا کد مخفی باشد
        state = await handle_special_inputs(update, context, ASK_PHONE)
        if state is not None:
            return state

        phone = (update.message.text or "").strip()

    context.user_data["phone"] = phone

    await ask_people_question(update, context)
    return ASK_PEOPLE


# گرفتن تعداد نفرات
async def get_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_special_inputs(update, context, ASK_PEOPLE)
    if state is not None:
        return state

    people = (update.message.text or "").strip()
    context.user_data["people"] = people

    await ask_nights_question(update, context)
    return ASK_NIGHTS


# گرفتن تعداد شب‌ها (اصلاح شده: عدد بودن و حداقل 3)
async def get_nights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # اول بررسی دکمه‌ها / کدهای مخفی
    state = await handle_special_inputs(update, context, ASK_NIGHTS)
    if state is not None:
        return state

    text = (update.message.text or "").strip()

    # بررسی عدد بودن
    if not text.isdigit():
        await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید (مثلاً: 3).")
        await ask_nights_question(update, context)
        return ASK_NIGHTS

    nights = int(text)

    # بررسی حداقل 3 شب
    if nights < 3:
        await update.message.reply_text("❌ زیر 3 شب مجاز نیست. لطفاً دوباره تعداد شب را وارد کنید.")
        await ask_nights_question(update, context)
        return ASK_NIGHTS

    # اگر معتبر بود، ذخیره و ادامه
    context.user_data["nights"] = nights

    await update.message.reply_text(f"✔ تعداد {nights} شب ثبت شد.")
    await ask_date_question(update, context)
    return ASK_DATE


# گرفتن تاریخ ورود
async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_special_inputs(update, context, ASK_DATE)
    if state is not None:
        return state

    date_text = (update.message.text or "").strip()
    context.user_data["date"] = date_text

    await ask_alt_contact_question(update, context)
    return ASK_ALT_CONTACT


# گرفتن راه ارتباطی مطمئن
async def get_alt_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_special_inputs(update, context, ASK_ALT_CONTACT)
    if state is not None:
        return state

    alt_contact = (update.message.text or "").strip()
    context.user_data["alt_contact"] = alt_contact

    await ask_fullname_question(update, context)
    return ASK_FULLNAME


# گرفتن نام و نام خانوادگی و اتمام
async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = await handle_special_inputs(update, context, ASK_FULLNAME)
    if state is not None:
        return state

    fullname = (update.message.text or "").strip()
    context.user_data["fullname"] = fullname

    user = update.effective_user

    # ساخت رکورد نهایی
    reservation = create_reservation_record(user, context.user_data, status="submitted")

    # ذخیره در JSON
    save_reservation_to_json(reservation)

    # متن برای ادمین
    summary = build_summary_text(reservation, canceled=False)

    # ارسال به ادمین
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary)
    except Exception as e:
        print("خطا در ارسال به ادمین:", e)

    # پیام به کاربر
    await update.message.reply_text(
        "اطلاعات شما با موفقیت ثبت شد.\n"
        "تا چند ساعت/دقیقه آینده پشتیبان ها با شما تماس میگیرند " \
        "برای ادمه و یا شروع دوباره  /start رو بزنید",
        reply_markup=None
    )

    return ConversationHandler.END


# /cancel یا دکمه «لغو درخواست ❌»
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ConversationHandler

    user = update.effective_user

    # رکورد لغوشده با اطلاعات تا این لحظه
    reservation = create_reservation_record(user, context.user_data, status="canceled")

    # ذخیره در JSON
    save_reservation_to_json(reservation)

    # متن برای ادمین
    summary = build_summary_text(reservation, canceled=True)

    # ارسال به ادمین
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary)
    except Exception as e:
        print("خطا در ارسال لغو به ادمین:", e)

    # پیام به کاربر
    await update.message.reply_text(
        "درخواست شما لغو شد. هر زمان خواستید می‌توانید دوباره از /start شروع کنید.",
        reply_markup=None
    )

    context.user_data.clear()
    return ConversationHandler.END


# ================== راه‌اندازی بات ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PHONE: [
                MessageHandler(
                    filters.CONTACT | (filters.TEXT & ~filters.COMMAND),
                    get_phone,
                )
            ],
            ASK_PEOPLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_people)
            ],
            ASK_NIGHTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_nights)
            ],
            ASK_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)
            ],
            ASK_ALT_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_alt_contact)
            ],
            ASK_FULLNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
