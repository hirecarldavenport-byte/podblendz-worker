AD_TERMS = [

    "sponsored by",
    "brought to you by",
    "thanks to our sponsor",
    "our sponsor",
    "support for this podcast",
    "this episode is sponsored",

    "promo code",
    "use code",
    "discount code",

    "home depot",
    "betterhelp",
    "shopify",
    "athletic greens",
    "ag1",
    "squarespace",

    "visit our sponsor",
    "special offer",
    "limited time offer",

    "advertisement",
    "paid partnership"

    "Sponsored by",
    "Brought to you by",
    "This episode is sponsored by",
    "Support for this episode comes from",
    "Thanks to our sponsor",
    "Paid partnership with",
    "Advertisement from",
    "A message from",
    "Presented by",
    "In partnership with"

    "Quick note from our sponsor",
    "Real quick — a word from our sponsor",
    "Before we continue, a message from",
    "If you like this show, you’ll love"
    "Want to [solve X]? Check out"
    "Here’s something that helped me"

    "Use code",
    "Promo code",
    "Enter code",
    "Get X% off with code"
    "Visit [brand] and use code",
    "Claim your special offer",
    "Limited time offer from",
    "Exclusive offer for listeners",

    "Visit our sponsor at",
    "Go to [short URL]",
    "Head to [brand].com",
    "Download the app and use code",
    "Sign up today at",
]


def looks_like_ad(text: str) -> bool:

    if not text:
        return False

    text = text.lower()

    return any(
        term in text
        for term in AD_TERMS
    )