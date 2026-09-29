"""Category definitions and rule repository for transaction classification.

Rules are kept completely isolated from engine processing logic.
Allows adding or updating merchant keywords and categories without
modifying the classifier code.
"""

from typing import Dict, List, Set

# Standard classification categories
CATEGORIES: List[str] = [
    "Food & Dining",
    "Shopping",
    "Travel",
    "Utilities",
    "Entertainment",
    "Healthcare",
    "Salary",
    "Investment",
    "Transfer",
    "ATM/Cash",
    "Fees & Charges",
    "Rent",
    "Education",
    "Other",
]

# Explicit keyword match lists per category (case-insensitive substring/token matching)
CATEGORY_RULES: Dict[str, List[str]] = {
    "Food & Dining": [
        "SWIGGY", "ZOMATO", "DOMINOS", "MCDONALDS", "KFC", "STARBUCKS",
        "BURGER KING", "PIZZA HUT", "SUBWAY", "HALDIRAM", "CHAAYOS", "CHAI POINT",
        "BLINKIT", "ZEPTO", "BIGBASKET", "INSTAMART", "GROCERS", "SUPERMARKET",
        "RESTAURANT", "CAFE", "BAKERY", "FOOD", "DINING", "EATERY", "DHABA",
        "SWEETS", "BARBEQUE NATION",
    ],
    "Shopping": [
        "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "MEESHO", "NYKAA",
        "TATA CLIQ", "RELIANCE DIGITAL", "CROMA", "DECATHLON", "ZARA",
        "H&M", "UNIQLO", "SHOPPERS STOP", "LIFESTYLE", "WESTSIDE",
        "IKEA", "PEPPERFRY", "PURPLLE", "LENSKART", "BEWAKOOF",
    ],
    "Travel": [
        "UBER", "OLA", "RAPIDO", "IRCTC", "MAKEMYTRIP", "GOIBIBO",
        "YATRA", "INDIGO", "AIR INDIA", "VISTARA", "SPICEJET", "AKASA",
        "CLEARTRIP", "REDBUS", "ABHIBUS", "METRO", "FASTAG", "NETC FASTAG",
        "INDIAN OIL", "IOCL", "BPCL", "HPCL", "SHELL", "PETROL", "FUEL",
        "TOLL PLAZA", "PARKING", "FLIGHT", "RAILWAYS",
    ],
    "Utilities": [
        "BESCOM", "TATA POWER", "ADANI ELECTRICITY", "MAHAVITARAN", "DHBVN",
        "ELECTRICITY", "POWER CORP", "WATER BOARD", "DJB", "BWSSB",
        "IGL", "MAHANAGAR GAS", "INDANE", "HP GAS", "BHARAT GAS", "PIPED GAS",
        "AIRTEL", "JIO", "VODAFONE", "VI PREPAID", "VI POSTPAID", "BSNL",
        "ACT FIBERNET", "HATHWAY", "TATA PLAY", "DISH TV", "RECHARGE", "BROADBAND",
    ],
    "Entertainment": [
        "NETFLIX", "SPOTIFY", "HOTSTAR", "DISNEY", "PRIME VIDEO",
        "BOOKMYSHOW", "PVR", "INOX", "CINEPOLIS", "YOUTUBE",
        "SONYLIV", "ZEE5", "APPLE MUSIC", "STEAM", "PLAYSTATION",
        "AMAZON PRIME", "AUDIBLE", "GAANA", "JIOSAAVN",
    ],
    "Healthcare": [
        "PHARMEASY", "1MG", "TATA 1MG", "APOLLO", "MEDPLUS", "NETMEDS",
        "PRACTO", "MAX HEALTHCARE", "FORTIS", "MANIPAL", "HOSPITAL",
        "CLINIC", "PHARMACY", "CHEMIST", "MEDS", "DIAGNOSTIC",
        "PATHOLOGY", "LAL PATHLABS", "DR LAL", "METROPOLIS", "DENTAL",
    ],
    "Salary": [
        "SALARY", "SALARY CREDIT", "PAYROLL", "CORP SALARY", "MONTHLY SALARY",
        "WAGES", "REMUNERATION", "CMS SALARY", "DIRECT DEPOSIT SALARY",
    ],
    "Investment": [
        "ZERODHA", "GROWW", "UPSTOX", "ANGEL ONE", "5PAISA", "MOTILAL OSWAL",
        "MUTUAL FUND", "MF", "SIP", "NPS", "PPF", "NSDL", "CDSL",
        "KFINTECH", "CAMS", "COIN", "SMALLCASE", "SAVINGS SCHEME",
        "FIXED DEPOSIT", "TERM DEPOSIT", "RECURRING DEPOSIT",
    ],
    "Transfer": [
        "UPI", "NEFT", "RTGS", "IMPS", "FUND TRANSFER", "P2P",
        "MONEY TRANSFER", "INTERNAL TRF", "SELF TRANSFER", "OWN A/C",
    ],
    "ATM/Cash": [
        "ATM CASH", "ATM WDL", "ATM WITHDRAWAL", "NFS ATM", "CASH WITHDRAWAL",
        "CASH DEP", "CASH DEPOSIT", "CDM CASH", "CASH AT BRANCH",
    ],
    "Fees & Charges": [
        "SERVICE CHARGE", "ANNUAL FEE", "SMS CHARGE", "PENALTY", "MIN BAL CHARGE",
        "CONVENIENCE FEE", "LATE PAYMENT FEE", "INTEREST DEBIT", "GST DEBIT",
        "CHEQUE BOUNCE", "PROCESSING FEE", "CARD ANNUAL FEE",
    ],
    "Rent": [
        "RENT", "HOUSE RENT", "FLAT RENT", "NOBROKER RENT", "MYGATE RENT",
        "CREDR RENT", "MAINTENANCE CHARGE", "SOCIETY MAINTENANCE",
    ],
    "Education": [
        "SCHOOL", "COLLEGE", "UNIVERSITY", "TUITION", "COACHING",
        "UDEMY", "COURSERA", "EDX", "UNACADEMY", "UPGRAD", "BYJU",
        "EXAM FEE", "ADMISSION FEE", "STUDENT FEES",
    ],
}
