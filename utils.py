""" Needs documentation
"""
import logging
from logging.handlers import TimedRotatingFileHandler
import sys

from ib.ext.Contract import Contract
__author__ = 'Jason Haury'


def make_contract(symbol):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = 'STK'
    contract.m_exchange = 'SMART'
    contract.m_primaryExch = 'SMART'
    contract.m_currency = 'USD'
    contract.m_localSymbol = symbol
    return contract

# ---------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def setup_logger(log):
    log.setLevel(logging.DEBUG)
    # Remove all other handlers:
    #for hdlr in logging.Logger.manager.loggerDict.keys():
    #    log.removeHandler(hdlr)

    # Add improved stdout logging
    '''
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    log.addHandler(ch)
    '''

    # Add rotating file log handler
    hdlr = TimedRotatingFileHandler('ibrest.log', when='D', backupCount=5)
    hdlr.setLevel(logging.DEBUG)
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    return log


def make_response(resp):
    """ Returns Flask tuple `resp, code` code per http://flask.pocoo.org/docs/0.10/quickstart/#about-responses
    """
    if 'errorMsg' in resp:
        # Bad request if arg which made it to TWS wasn't right
        return resp, 400
    else:
        return resp


