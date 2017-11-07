#!/usr/bin/python

import sys
import yaml
import requests
import argparse
import logging
import logging.handlers

DEFAULT_APIBASE = 'https://api.aprs.fi/api/'
DEFAULT_USER_AGENT = 'aprsfi-py-api-client 1.0'

class APRSFIClient(object):
    """
    Post objects to aprs.fi using the REST API. Note that this API is
    currently not available on the main aprs.fi site.
    """
    def __init__(self, logger = None, apibase = DEFAULT_APIBASE, apikey = None, basicauth_user = None, basicauth_pass = None, user_agent = DEFAULT_USER_AGENT):
        self.log = logger
        self.apibase = apibase
        self.apikey = apikey
        
        if basicauth_user and basicauth_pass:
            self.basic_auth = (basicauth_user, basicauth_pass)
        else:
            self.basic_auth = None
        
        self.user_agent = user_agent
    
    def api_req(self, url, url_params, postdata = None, loginfo = ''):
        url_full = self.apibase + url
        headers = {
            'User-Agent': self.user_agent
        }
        url_params['apikey'] = self.apikey
        
        try:
            r = requests.post(url_full, params = url_params, json = postdata, auth = self.basic_auth,
                headers = headers, timeout = 30)
            r.raise_for_status()
            rdata = r.json()
            if rdata.get('result') == 'ok':
                self.log.info("OK: %s got %d: %s" % (loginfo, r.status_code, r.text))
            else:
                self.log.error("FAIL: %s got %d: %s" % (loginfo, r.status_code, r.text))
        except requests.exceptions.HTTPError as exc:
            self.log.error("FAIL HTTP: %s: %r", loginfo, exc)
            return
        except Exception as exc:
            self.log.error("FAIL HTTP: %s: %r", loginfo, exc)
            return
            
    def post_object(self, obj):
        self.api_req("post", {"what": "loc"}, {
            'type': 'o',
            'name': obj.get('name'),
            'comment': obj.get('comment'),
            'symbol': obj.get('symbol'),
            'locs': [
                {
                    'lat': obj.get('lat'),
                    'lng': obj.get('lon'),
                }
            ]
        }, loginfo = "post loc '%s'" % obj.get('name'))
    
    def process_yaml(self, yo):
        objects = yo.get("objects", [])
        for obj in objects:
            self.post_object(obj)
    
    def process_file(self, fname):
        with open(fname, 'r') as stream:
            try:
                yo = yaml.load(stream)
            except yaml.YAMLError as exc:
                self.log.error("YAML failure for %s: %r", fname, exc)
                return
            
            self.process_yaml(yo)
            
    def process_url(self, url):
        
        try:
            r = requests.get(url, timeout = 30)
            r.raise_for_status()
            yo = yaml.load(r.text)
        except yaml.YAMLError as exc:
            self.log.error("YAML failure for %s: %r", url, exc)
            return
        except requests.exceptions.HTTPError as exc:
            self.log.error("YAML HTTP error for %s: %r", url, exc)
            return
        except Exception as exc:
            self.log.error("YAML exception for %s: %r", url, exc)
            return
        
        self.process_yaml(yo)

def get_logger():
    log = logging.getLogger('aprsfi-api-client')
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s: %(levelname)s - %(message)s')
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(formatter)
    
    log.addHandler(handler)
    
    return log
    
def main():
    parser = argparse.ArgumentParser(description='Upload data to aprs.fi API')
    parser.add_argument('--api-key', dest='api_key', type=str, help='API key')
    parser.add_argument('--base-url', dest='base_url', type=str, default=DEFAULT_APIBASE, help='API base URL')
    parser.add_argument('--input-file', dest='input_file', type=str, help='YAML file path')
    parser.add_argument('--input-url', dest='input_url', type=str, help='YAML file URL')
    # only used in testing environment
    parser.add_argument('--basicauth-user', dest='basicauth_user', type=str, help='debug/test env: username')
    parser.add_argument('--basicauth-pass', dest='basicauth_pass', type=str, help='debug/test env: password')

    args = parser.parse_args()
    
    logger = get_logger()
    
    ayo = APRSFIClient(logger = logger, apibase = args.base_url, apikey = args.api_key, basicauth_user = args.basicauth_user, basicauth_pass = args.basicauth_pass)
    if args.input_file:
        ayo.process_file(args.input_file)
    if args.input_url:
        ayo.process_url(args.input_url)

main()

