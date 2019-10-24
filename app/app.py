import requests
from flask import Flask, session, request, Response, abort, jsonify, make_response
from functools import wraps
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#------------- Required envs
#Unifi hotspot user and password
UNIFI_HOTSPOT_USER = os.environ['UNIFI_HOTSPOT_USER']
UNIFI_HOTSPOT_PASS = os.environ['UNIFI_HOTSPOT_PASS']
UNIFI_URL = os.environ['UNIFI_URL']

#User and password for basic auth.
HTTP_USER = os.environ['HTTP_USER']
HTTP_PASS = os.environ['HTTP_PASS']

#Optional envs
DEBUG = os.getenv('DEBUG', False)
BIND_IP = os.getenv('BIND_IP', '0.0.0.0')
BIND_PORT = os.getenv('BIND_PORT', 5000)
UNIFI_SITE = os.getenv('UNIFI_SITE', 'default')
VERIFY_CERT = False if os.getenv('VERIFY_CERT') == 'False' or os.getenv('VERIFY_CERT') == 'false' else True

#------------ Auth

def check_auth(username, password):
	return (username == HTTP_USER and password == HTTP_PASS)

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Unauthorized', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def unifi_login(s):
    response = s.post(UNIFI_URL + '/api/login',
            json={"username": UNIFI_HOTSPOT_USER,
                "password": UNIFI_HOTSPOT_PASS,
                "strict":"true",
                "for_hotspot":"true",
                "site_name": UNIFI_SITE,
                "remember":"true"},
            headers={'Content-Type': 'application/json'},
            verify=VERIFY_CERT
            ).json()
    if response['meta']['rc'] == 'error':
        return False
    elif response['meta']['rc'] == 'ok':
        return True
    else:   
        raise Exception('Unexpected response code.')

#------------


app = Flask('unifi-vouchers-http-api') 
app.secret_key = os.urandom(50)

#Create session object to store auth cookie.
s = requests.Session()


@app.route('/api/voucher', methods=['POST'])
@requires_auth
def get_voucher():
    """
    Parameters (HTTP)
    ----------
    voucher_duration
        Duration of the voucher.
    unit : (minutes, hours, days)
        Unit used for the duration of the voucher.
    note : optional
        Note for the voucher.

    Returns
    ----------
        {
            "voucher_code": <voucher_number>
        }
    """
    try:
        s.cookies.get_dict()['unifises']
    except KeyError:
        if not unifi_login(s):
            abort(make_response(jsonify(message="Wrong Unifi hotspot username or password."), 403))


    # note is optional.
    try:
        note = request.form['note']
    except KeyError:
        note = ''

    # return 400 if mandatory parameters are not in the request.
    try:
        voucher_duration = int(request.form['voucher_duration'])
        unit = request.form['unit']
    except KeyError:
        abort(make_response(jsonify(message="voucher_duration and unit are mandatory parameters"), 400))

    #convert voucher_duration to minutes
    if unit == 'minutes':
        expire_number = voucher_duration
    elif unit == 'hours':
        expire_number = voucher_duration * 60
    elif unit == 'days':
        expire_number = voucher_duration * 60 * 24
    else:
        abort(make_response(jsonify(message="unrecognized unit. Must be one of: minutes, hours or days"), 400))
    
    expire_number = str(expire_number)

    response = s.post(UNIFI_URL + '/api/s/{0}/cmd/hotspot'.format(UNIFI_SITE),
        json={"cmd":"create-voucher","n":1,"quota":1,"expire":"custom","expire_number": expire_number,"expire_unit":1,"note": note},
        headers={'Content-Type': 'application/json'},
        verify=VERIFY_CERT
        ).json()
    
    #cookie is expired, login and try again.
    if response['meta']['rc'] == 'error' and response['meta']['msg'] == 'api.err.LoginRequired':
        unifi_login(s)
        response = s.post(UNIFI_URL + '/api/s/{0}/cmd/hotspot'.format(UNIFI_SITE),
            json={"cmd":"create-voucher","n":1,"quota":1,"expire":"custom","expire_number": expire_number,"expire_unit":1,"note": note},
            headers={'Content-Type': 'application/json'},
            verify=VERIFY_CERT
            ).json()

    create_time = response['data'][0]['create_time']


    #list tokens and return the one we just created.
    response = s.get(UNIFI_URL + '/api/s/{0}/stat/voucher'.format(UNIFI_SITE)).json()
    for token in response['data']:
        if token['create_time'] == create_time:
            return jsonify({"voucher_code": token['code']})
    else:
        abort(500)

    

if __name__ == "__main__":
    app.run(debug=DEBUG, host=BIND_IP, port=BIND_PORT)