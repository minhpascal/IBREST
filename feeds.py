""" In case of IB EClientSocket requests which generate continuous feeds of data, this module will generate atom feeds.
"""
__author__ = 'Jason Haury'

# Globals to use for feed responses
_market_resp = {c: [] for c in xrange(8)}  # market feed
_tickerId = 0


# ---------------------------------------------------------------------
# MESSAGE HANDLERS
# ---------------------------------------------------------------------
def market_handler(msg):
    """ Update our global Market data response dict
    """
    resp = dict()
    for i in msg.items():
        resp[i[0]] = i[1]
    _market_resp.append(resp.copy())


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
    contract = create_contract(str(symbol), secType='CASH', exchange='IDEALPRO', currency='USD') #, prim_exch='NASDAQ')
    #contractTuple = ('EUR', 'CASH', 'IDEALPRO', 'USD', '', 0.0, '')
    #contract = makeStkContract(contractTuple)
    # The tickerId must be unique, so just increment our global to guarantee uniqueness
    global _tickerId
    _tickerId += 1
    global _market_resp
    _market_resp = []
    log.info('Requesting market data')
    #client.reqMktData(_tickerId, contract, '100', True)
    time.sleep(1)
    client.reqMktData(1, contract, '', False)
    #client.reqMktData(_tickerId, contract, '', False)
    while len(_market_resp) < 5 and client.isConnected() is True:
        log.info("Waiting for responses on {}...".format(client))
        time.sleep(1)
    print 'disconnected', close_client(client)
    return _market_resp