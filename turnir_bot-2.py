@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return

    builder = InlineKeyboardBuilder()

    builder.button(text="👥 Foydalanuvchilar", callback_data="adm_users")
    builder.button(text="📊 Statistika", callback_data="adm_stats")

    builder.button(text="🎁 Ball qo'shish", callback_data="adm_addball")
    builder.button(text="❌ Ball ayirish", callback_data="adm_removeball")

    builder.button(text="📢 Reklama", callback_data="adm_ad")
    builder.button(text="🔍 Qidirish", callback_data="adm_search")

    builder.button(text="🏆 Turnir yaratish", callback_data="adm_tournament")
    builder.button(text="📅 Turnirlar", callback_data="adm_tournaments")

    builder.adjust(2)

    await message.answer(
        "⚙️ Admin Panel",
        reply_markup=builder.as_markup()
    )