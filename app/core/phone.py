def format_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    # If starts with 0, replace with +61 (Australia)
    if phone.startswith("0"):
        return "+61" + phone[1:]
    # Otherwise just add +
    return "+" + phone
