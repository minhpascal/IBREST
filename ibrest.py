""" Wrapper on IbPy to do heavy lifting for our Flask app
"""
from ib.opt import ibConnection, message
from ib.ext.Contract import Contract
from ib.ext.Order import Order
import time
from app import app

__author__ = 'jhaury'

# ---------------------------------------------------------------------
# GLOBAL PARAMETERS
# ---------------------------------------------------------------------
# Mutables
_clientId_pool = {0, 1, 2, 3, 4, 5, 6, 7}
_tickerId = 0
# We also have some (dangerously) global dicts to use for our responses as updated by Message handlers
_market_resp = dict()
_portfolio_positions_resp = dict()

# ---------------------------------------------------------------------
# MESSAGE HANDLERS
# ---------------------------------------------------------------------
def my_account_handler(msg):
    # ... do something with account msg ...
    print msg


def market_handler(msg):
    """ Update our global Market data response dict
    """
    print "msg: {}".format(dir(msg), msg)
    resp = dict(tickerId = msg.tickerId, field=msg.field, price=msg.price, canAutoExecute=msg.canAutoExecute)
    _market_resp['tickPrice'] = resp.copy()


def portfolio_positions_handler(msg):
    """ Update our global Portfolio Positoins data response dict
    """

    if msg.typeName == 'position':
        position = dict()
        for i in msg.items():
            if isinstance(i[1], Contract):
                position[i[0]] = i[1].__dict__
            else:
                position[i[0]] = i[1]
        _portfolio_positions_resp['position'].append(position.copy())
    elif msg.typeName == 'positionEnd':
        _portfolio_positions_resp['positionEnd'] = True
    app.logger.info('POSITION: {})'.format(msg))

    ''' POSITION: <positionEnd>, ['__assoc__', '__class__', '__delattr__', '__doc__', '__format__', '__getattribute__',
    '__hash__', '__init__', '__len__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__',
    '__sizeof__', '__slots__', '__str__', '__subclasshook__', 'items', 'keys', 'typeName', 'values'])
    '''

def error_handler(msg):
    app.logger.error(msg)


def generic_handler(msg):
    app.logger.info('MESSAGE: {}, {})'.format(msg, msg.keys))


# ---------------------------------------------------------------------
# SHARED FUNCTIONS
# ---------------------------------------------------------------------
def get_client(client_id=None):
    """ Creates a client connection to be used with orders
    """
    if client_id is None:
        # Get client ID from our pool list in memory
        try:
            client_id = _clientId_pool.pop()
        except KeyError:
            client_id = None
    if client_id is None:
        return
    app.logger.info('Attempting connection with client_id {}'.format(client_id))
    #client = ibConnection('104.196.34.62', 4001, client_id)
    client = ibConnection('172.17.0.1', 4001, client_id)
    #client = ibConnection('localhost', 4001, client_id)

    # Add all our handlers
    # TODO add specific handlers
    client.register(market_handler, 'TickSize', 'TickPrice')
    client.register(portfolio_positions_handler, 'Position', 'PositionEnd')
    client.register(error_handler, 'Error')
    client.registerAll(generic_handler)
    client.connect()
    client.enableLogging()
    '''
    if client is None:
        # Somehow we didn't make a connection so return None
        return
    '''

    app.logger.info('Client: {}'.format(client))
    # TODO check if client is connected.  use .disconnect() if useful then reconnect.
    return client


def close_client(client):
    """ Get's ID from memcache
    """
    client_id = client.clientId
    # add our client_id back into ourpool
    _clientId_pool.add(client_id)

    # Now close our actual client
    client.close()
    return client_id


# ---------------------------------------------------------------------
# MARKET DATA FUNCTIONS
# ---------------------------------------------------------------------
# From https://www.quantstart.com/articles/using-python-ibpy-and-the-interactive-brokers-api-to-automate-trades
def create_contract(symbol, sec_type, exch, prim_exch, curr):
    """ Create a Contract object defining what will
    be purchased, at which exchange and in which currency.

    symbol - The ticker symbol for the contract
    sec_type - The security type for the contract ('STK' is 'stock')
    exch - The exchange to carry out the contract on
    prim_exch - The primary exchange to carry out the contract on
    curr - The currency in which to purchase the contract """
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = sec_type
    contract.m_exchange = exch
    contract.m_primaryExch = prim_exch
    contract.m_currency = curr
    return contract

def create_order(order_type, quantity, action):
    """ Create an Order object (Market/Limit) to go long/short.

    order_type - 'MKT', 'LMT' for Market or Limit orders
    quantity - Integral number of assets to order
    action - 'BUY' or 'SELL' """
    order = Order()
    order.m_orderType = order_type
    order.m_totalQuantity = quantity
    order.m_action = action
    return order


def get_market_data(symbol):
    """ The m_symbol for the contract is all our API takes from user (for mow)
    """
    # TODO consider taking more args to get our market data with
    app.logger.info('Getting market data for {}'.format(symbol))
    # Connect to TWS
    client = get_client()
    if client is None:
        return {'error': 'No connection'}
    app.logger.info('Creating Contract')
    contract = create_contract(symbol, sec_type='STK', exch='Smart', prim_exch='NASDAQ', curr='USD')
    # The tickerId must be unique, so just increment our global to guarantee uniqueness
    global _tickerId
    _tickerId += 1
    _market_resp = dict()
    app.logger.info('Requesting market data')
    client.reqMktData(_tickerId, contract, '', True)
    while len(_market_resp) == 0 and client.isConnected is True:
        app.logger.info("Waiting for responses on {}...".format(client))
        time.sleep(1)
    print 'disconnected', close_client(client)
    return _market_resp



# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_order_id():
    """ Gets next valid for an order.  Looks at memcache or calls nextValidId()
    """
    pass


def order_trail_stop(symbol, trailing_percent):
    """ Places a trailing stop loss order
    """
    # Get our next order ID
    order_id = get_order_id()

    # Get a clientId from our memcache pool
    # TODO create a memcache set of 1000 clientIds used for orders.
    # TODO Pop an ID off when connecting, then append it back when disconnecting
    client_id = 0

    # Open a connection
    client = get_client()

    # Create a contract object
    # Update the parameters to be sent to the Market Order request
    order_ticker = Contract()
    order_ticker.m_symbol = symbol
    order_ticker.m_secType = 'STK'
    order_ticker.m_exchange = 'SMART'
    order_ticker.m_primaryExch = 'SMART'
    order_ticker.m_currency = 'USD'
    order_ticker.m_localSymbol = symbol

    # Create an order object
    # Update the parameters to be sent to the Market Order request
    order_desc = Order()
    order_desc.m_minQty = 100
    order_desc.m_lmtPrice = 11.00
    order_desc.m_orderType = 'LMT'
    order_desc.m_totalQuantity = 100
    # TODO set m_action based on input arg (and relate to long/short)
    order_desc.m_action = 'SELL'
    order_desc.m_trailingPercent = trailing_percent

    client.placeOrder(order_id, order_ticker, order_desc)

    print 'disconnected', close_client(client)
    # TODO add client_id back to memcache pool


# ---------------------------------------------------------------------
# PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio():
    app.logger.info('Getting client')
    client = get_client()
    app.logger.info('Got client, getting portfolio')
    global _portfolio_positions_resp
    _portfolio_positions_resp = dict(positionEnd=False, position=[])
    client.reqPositions()
    #app.logger.info('Closing client')
    #close_client(client)
    while _portfolio_positions_resp['positionEnd'] is False:
        app.logger.info("Waiting for responses on {}...".format(client))
        time.sleep(1)
    close_client(client)
    return _portfolio_positions_resp

#connection = ibConnection('104.196.34.62', 4001, 5)
#connection.registerAll(my_generic_handler)
# connection.register(my_account_handler, 'UpdateAccountValue')
# connection.register(my_tick_handler, 'TickSize', 'TickPrice')
#connection.connect()
#connection = get_client()
# connection.reqAccountUpdates(True, 'DU256159')
#connection.reqPostions()
