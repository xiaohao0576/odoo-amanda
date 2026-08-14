PAYMENT_METHODS_MAPPING = {
    'card': 'cards',
    'abapay_khqr': 'abapay_khqr',
    'wechat_pay': 'wechat',
    'alipay': 'alipay',
}

PAYWAY_PAYMENT_METHODS_MAPPING = {
    'visa': 'visa',
    'mastercard': 'mc',
    'unionpay': 'cup',
    'jcb': 'jcb',
}

DEFAULT_PAYMENT_METHODS_CODES = {
    'card',
    'abapay_khqr',
    'wechat_pay',
    'alipay',

    # Brand payment methods.
    'visa',
    'mastercard',
    'unionpay',
    'jcb',
}

PURCHASE_PAYMENT_SECURE_HASH_KEYS = [
    'req_time',
    'merchant_id',
    'tran_id',
    'amount',
    'firstname',
    'lastname',
    'email',
    'phone',
    'type',
    'payment_option',
    'return_url',
    'continue_success_url',
    'currency',
    'lifetime',
    'skip_success_page',
]

SUPPORTED_CURRENCIES = {
    'KHR',
    'USD',
}

CURRENCY_DECIMALS = {
    'KHR': 0,
    'USD': 2,
}

WEB_HOOK_PATH = {
    'webhook': '/payment/payway/webhook',
    'poll': '/payment/payway/status/poll',
}

STATUS_MAPPING = {
    'APPROVED': 'APPROVED',
    'PRE-AUTH': 'PRE-AUTH',
    'REFUNDED': 'REFUNDED',
    'PENDING': 'PENDING',
    'CANCELLED': 'CANCELLED',
}

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
PAYWAY_TRAN_ID_MAX_LENGTH = 20

API_URLS = {
    'production': 'https://checkout.payway.com.kh',
    'sandbox': 'https://checkout-sandbox.payway.com.kh',
}

REFUND_TXN_SECURE_HASH_KEYS = ['request_time', 'merchant_id', 'merchant_auth']
CHECK_TXN_SECURE_HASH_KEYS = ['req_time', 'merchant_id', 'tran_id']
VOID_TXN_SECURE_HASH_KEYS = ['merchant_id', 'merchant_auth', 'request_time']
CAPTURE_TXN_SECURE_HASH_KEYS = ["merchant_auth", "request_time", "merchant_id"]