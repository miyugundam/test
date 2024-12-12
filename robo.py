async def fetch_peer_details(update: Update, context: CallbackContext):
    peer_name = update.message.text  # User-provided peer name
    response = api_request(f"api/peers?config=wg0.conf&page=1&limit=50")  # Fetch all peers (adjust limit as needed)

    if "error" in response:
        await update.message.reply_text(f"❌ Error fetching peers: {response['error']}")
        return SELECT_PEER

    peers = response.get("peers", [])
    matched_peer = None

    # Search for the peer by name
    for peer in peers:
        if peer.get("peer_name") == peer_name:
            matched_peer = peer
            break

    if not matched_peer:
        await update.message.reply_text("❌ Peer not found. Please enter a valid peer name:")
        return SELECT_PEER

    # Save the matched peer details in user_data
    context.user_data["peer_name"] = peer_name
    context.user_data["peer_details"] = matched_peer

    # Format peer details as HTML
    fields = "\n".join(
        [
            f"{i+1}. <b>{key.capitalize()}</b>: {value}"
            for i, (key, value) in enumerate(matched_peer.items())
        ]
    )
    message = f"🔧 <b>Peer Details</b>\n\n{fields}\n\nSend the <b>number</b> of the field you want to edit:"
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="edit_peer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
    return SELECT_FIELD
