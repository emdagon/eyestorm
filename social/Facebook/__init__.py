
import hmac

from hashlib import sha256

import tornado.escape

from eyestorm import web


def parse_signed_request(signed_request, secret):
    """Handles the Facebook "signed_request" parameter used on some situations.
    See http://developers.facebook.com/docs/authentication/signed_request/ for
    more information.

    """
    encoded_sig, payload = signed_request.split('.')

    # decode data
    sig = web.base64_url_decode(encoded_sig)
    data = tornado.escape.json_decode(web.base64_url_decode(payload))

    if data['algorithm'].upper() != 'HMAC-SHA256':
        raise ValueError('Unknown algorithm. Expected HMAC-SHA256')

    # check sig
    expected_sig = hmac.new(secret, payload, sha256).digest()
    if sig != expected_sig:
        raise StandardError('Bad Signed JSON signature!')

    return data
