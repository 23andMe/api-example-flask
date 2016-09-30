#!/usr/bin/python

import getpass
import requests
import flask
from flask import request
import os
from optparse import OptionParser
from requests_oauthlib import OAuth2Session

PORT = 5000
API_SERVER = 'api.23andme.com'
BASE_CLIENT_URL = 'http://localhost:%s/' % PORT
DEFAULT_REDIRECT_URI = '%sreceive_code/' % BASE_CLIENT_URL

# so we don't get errors if the redirect uri is not https
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = '1'

#
# you can pass in more scopes through the command line, or change these
#
DEFAULT_SNPS = ['rs12913832']
DEFAULT_SCOPES = ['names', 'basic'] + DEFAULT_SNPS

#
# the command line will ask for a client_secret if you choose to not hardcode the app's client_secret here
#
client_secret = None

parser = OptionParser(usage="usage: %prog -i CLIENT_ID [options]")
parser.add_option("-i", "--client-id", dest="client_id", default='',
                  help="Your client_id [REQUIRED]")
parser.add_option('-s', '--scopes', dest='scopes', action='append', default=[],
                  help='Your requested scopes. Eg: -s basic -s rs12913832')
parser.add_option("-r", "--redirect_uri", dest="redirect_uri", default=DEFAULT_REDIRECT_URI,
                  help="Your client's redirect_uri [%s]" % DEFAULT_REDIRECT_URI)
parser.add_option("-a", "--api_server", dest="api_server", default=API_SERVER,
                  help="Almost always: [api.23andme.com]")
parser.add_option("-p", "--select-profile", dest='select_profile', action='store_true', default=False,
                  help='If present, the auth screen will show a profile select screen')

(options, args) = parser.parse_args()
BASE_API_URL = "https://%s" % options.api_server
API_AUTH_URL = '%s/authorize' % BASE_API_URL
API_TOKEN_URL = '%s/token/' % BASE_API_URL

if options.select_profile:
    API_AUTH_URL += '?select_profile=true'

redirect_uri = options.redirect_uri
client_id = options.client_id

scopes = options.scopes or DEFAULT_SCOPES

if not options.client_id:
    print "missing param: CLIENT_ID:"
    parser.print_usage()
    print "Please navigate to your developer dashboard [%s/dev/] to retrieve your client_id.\n" % BASE_API_URL
    exit()

if not client_secret:
    print "Please navigate to your developer dashboard [%s/dev/] to retrieve your client_secret." % BASE_API_URL
    client_secret = getpass.getpass("Please enter your client_secret:")

app = flask.Flask(__name__)


@app.route('/')
def index():
    ttam_oauth = OAuth2Session(client_id,
                               redirect_uri=redirect_uri,
                               scope=scopes)
    auth_url, state = ttam_oauth.authorization_url(API_AUTH_URL)
    return flask.render_template('index.html', auth_url=auth_url)


@app.route('/receive_code/')
def receive_code():
    #
    # now we hit the /token endpoint to get the access_token
    #
    ttam_oauth = OAuth2Session(client_id,
                               redirect_uri=redirect_uri)
    token_dict = ttam_oauth.fetch_token(API_TOKEN_URL,
                                        client_secret=client_secret,
                                        authorization_response=request.url)

    #
    # the response token_dict is of the form
    # {
    #     'token_type': 'bearer',
    #     'refresh_token': '7cb92495fe515f0bfe94775e2b06b46b',
    #     'access_token': 'ad7ace51ad19732b3f9ef778dc766fce',
    #     'scope': ['rs12913832', 'names', 'basic'],
    #     'expires_in': 86400, 'expires_at': 1475283697.571757
    # }
    #

    access_token = token_dict['access_token']

    #
    # now you have the access_token to make queries with
    # enter your code here
    #
    # the following is a sample of how you can use the access_token to make your API queries
    # it makes query to the /genotype endpoint and gets information about the requested SNPS
    #
    headers = {'Authorization': 'Bearer %s' % access_token}
    genotype_response = requests.get("%s%s" % (BASE_API_URL, "/1/genotype/"),
                                     params={'locations': ' '.join(DEFAULT_SNPS)},
                                     headers=headers,
                                     verify=False)
    if genotype_response.status_code == 200:
        return flask.render_template('receive_code.html', response_json=genotype_response.json())
    else:
        # print 'response text = ', genotype_response.text
        genotype_response.raise_for_status()


if __name__ == '__main__':
    print "A local client for the Personal Genome API is now initialized."
    app.run(debug=False, port=PORT)
