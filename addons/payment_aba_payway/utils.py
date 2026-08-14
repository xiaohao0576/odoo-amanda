import time
from odoo import fields
from odoo.addons.payment_aba_payway import const

def _compute_payway_tran_id(prefix, separator='-',):
    """ Generate unique tran_id for payway, by suffixing the prefix with the current timestamp in base62.

    :param str prefix: The custom prefix for the tran_id
    :param str separator: The custom separator
    :return: The generated tran_id
    :rtype: str
    """

    # Use custom prefix, by convert timestamp to base62
    # preserve Odoo original reference in PayWay transaction id for easy reconciliation.
    # Also ensure consitency with PayWay transaction id for POS module (Same prefix format).    
    suffix = _compute_transaction_suffix()
    len_suffix = len(suffix)
    prefix = prefix[:const.PAYWAY_TRAN_ID_MAX_LENGTH-len(separator)-len_suffix]
    return f'{prefix}{separator}{suffix}'


def to_base62(n: int) -> str:
    if n == 0:
        return const.BASE62_ALPHABET[0]
    
    base62 = []
    while n > 0:
        n, r = divmod(n, 62)
        base62.append(const.BASE62_ALPHABET[r])
    
    return ''.join(reversed(base62))

def _compute_transaction_suffix():
        """Convert timestamp into base62, for suffix transaction reference.

        :rtype: str
        """
        
        timestamp = int(time.time())
        encoded = to_base62(timestamp)
        return encoded