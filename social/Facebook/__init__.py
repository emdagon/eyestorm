#!/bin/env python
#
# Copyright 2012 Emilio Daniel Gonzalez (@emdagon)
#
# This file is part of Eyestorm.
#
# Eyestorm is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Eyestorm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Eyestorm.  If not, see <http://www.gnu.org/licenses/>.

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
