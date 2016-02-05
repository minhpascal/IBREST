""" In case of IB EClientSocket requests which generate continuous feeds of data, this module will generate atom feeds.
"""
import globals as g
import time
import logging
import utils
from connection import get_client, close_client
from utils import make_contract

__author__ = 'Jason Haury'
log = logging.getLogger(__name__)
log = utils.setup_logger(log)

# ---------------------------------------------------------------------
# MARKET DATA FUNCTIONS
# ---------------------------------------------------------------------
# TODO This needs to be a feed, not an endpoint.   http://flask.pocoo.org/snippets/10/ . Use GAE memcache.
def get_market_data(symbol):
    """ The m_symbol for the contract is all our API takes from user (for now).
    User must have appropriate IB subscriptions.
    """
    # TODO consider taking more args to get our market data with
    log.debug('Getting market data for {}'.format(symbol))
    # Connect to TWS
    client = get_client()
    if client.isConnected() is False:
        return {'error': 'Not connected to TWS'}
    log.debug('Creating Contract for symbol {}'.format(symbol))
    contract = make_contract(str(symbol)) #, prim_exch='NASDAQ')
    #contractTuple = ('EUR', 'CASH', 'IDEALPRO', 'USD', '', 0.0, '')
    #contract = makeStkContract(contractTuple)
    # The tickerId must be unique, so just increment our global to guarantee uniqueness
    g.tickerId += 1

    g.market_resp = []
    log.info('Requesting market data')
    #client.reqMktData(tickerId, contract, '100', True)
    time.sleep(1)
    client.reqMktData(1, contract, '', False)
    #client.reqMktData(tickerId, contract, '', False)
    while len(g.market_resp) < 5 and client.isConnected() is True:
        log.info("Waiting for responses on {}...".format(client))
        time.sleep(1)
    print 'disconnected', close_client(client)
    return g.market_resp