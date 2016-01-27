""" Wrapper on IbPy to do heavy lifting for our Flask app
"""
from ib.opt import ibConnection, message
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.OrderState import OrderState
import time
from app import app
import os

__author__ = 'jhaury'


# ---------------------------------------------------------------------
# GLOBAL PARAMETERS
# ---------------------------------------------------------------------
# Configuration
# Either use environment variables
_ibgw_host = os.getenv('IBGW_HOST', '127.0.0.1')
_ibgw_port = int(os.getenv('IBGW_PORT', '4001'))

# ...Or override them with hard-coded values
#_ibgw_host = '104.196.34.62'
#_ibgw_host = '172.17.0.1'
#_ibgw_host = '172.17.0.2'

#_ibgw_port = 4001  # IB Gateway
#_ibgw_port = 7496  # TWS

# Mutables
_managedAccounts = []
_clientId_pool = {0, 1, 2, 3, 4, 5, 6, 7}
_tickerId = 0
_orderId = 0

# Responses.  We also have some (dangerously) global dicts to use for our responses as updated by Message handlers
_market_resp = []
_portfolio_positions_resp = dict()
_order_resp = dict(openOrderEnd=False, openOrder=[], openStatus=[])

# Logging shortcut
log = app.logger


# ---------------------------------------------------------------------
# MESSAGE HANDLERS
# ---------------------------------------------------------------------
def connection_handler(msg):
    """ Handles messages from when we connect to TWS
    """
    if msg.typeName == 'nextValidId':
        global _orderId
        _orderId = int(msg.orderId)
        log.info('Updated orderID: {}'.format(_orderId))
    elif msg.typeName == 'managedAccounts':
        global _managedAccounts
        _managedAccounts = msg.accountsList.split(',')
        log.info('Updated managed accounts: {}'.format(_managedAccounts))


def market_handler(msg):
    """ Update our global Market data response dict
    """
    resp = dict()
    for i in msg.items():
        resp[i[0]] = i[1]
    _market_resp.append(resp.copy())


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
        _portfolio_positions_resp['positions'].append(position.copy())
    elif msg.typeName == 'positionEnd':
        _portfolio_positions_resp['positionEnd'] = True
    log.info('POSITION: {})'.format(msg))


def order_handler(msg):
    """ Update our global Order data response dict
    """
    global _order_resp
    if msg.typeName in ['openStatus', 'openOrder']:
        d = dict()
        for i in msg.items():
            if isinstance(i[1], (Contract, Order, OrderState)):
                d[i[0]] = i[1].__dict__
            else:
                d[i[0]] = i[1]
        _order_resp[msg.typeName].append(d.copy())
    elif msg.typeName == 'openOrderEnd':
        _order_resp['openOrderEnd'] = True
    log.info('ORDER: {})'.format(msg))


def error_handler(msg):
    log.error(msg)


def generic_handler(msg):
    log.info('MESSAGE: {}, {})'.format(msg, msg.keys))


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
    log.info('Attempting connection with client_id {}'.format(client_id))
    client = ibConnection(_ibgw_host, _ibgw_port, client_id)

    # Add all our handlers
    # TODO add specific handlers
    client.register(connection_handler, 'ManagedAccounts', 'NextValidId')
    client.register(market_handler, 'TickSize', 'TickPrice')
    client.register(order_handler, 'OpenOrder', 'OrderStatus', 'OpenOrderEnd')
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


# From https://www.quantstart.com/articles/using-python-ibpy-and-the-interactive-brokers-api-to-automate-trades
# TODO decide what the args are truly needed.
def create_contract(symbol, secType='STK', exchange='SMART', currency='USD'):  #, prim_exch):
    """ Create a Contract object defining what will
    be purchased, at which exchange and in which currency.

    symbol - The ticker symbol for the contract
    secType - The security type for the contract ('STK' is 'stock')
    exchange - The exchange to carry out the contract on
    prim_exch - The primary exchange to carry out the contract on
    currency - The currency in which to purchase the contract """
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = secType
    contract.m_exchange = exchange
    #contract.m_primaryExch = prim_exch
    contract.m_currency = currency
    contract.m_expiry = ''
    contract.m_strike = 0.0
    contract.m_right = ''
    return contract


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


# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_open_orders():
    """ Uses reqAllOpenOrders to get all open orders from 
    """
    global _order_resp
    client = get_client()
    client.reqAllOpenOrders()
    while _order_resp['openOrderEnd'] is False and client.isConnected() is True:
        log.info("Waiting for responses on {}...".format(client))
        time.sleep(0.5)
    close_client(client)
    resp = _order_resp.copy()
    # Reset our order resp for next time
    _order_resp = dict(openOrderEnd=False, openOrder=[], openStatus=[])
    print resp
    return resp


def order_trail_stop(symbol, qty, stopPrice, trailingPercent):
    """ Places a trailing stop loss order.  `qty` used to determine BUY/SELL, and both *Quantity inputs.
    """
    # Open a connection
    client = get_client()
    time.sleep(0.5)

    # Create a contract object
    contract = create_contract(symbol)

    # Create an order object
    # Update the parameters to be sent to the Market Order request
    order = Order()
    order.m_action = 'BUY' if qty > 0 else 'SELL'
    order.m_minQty = abs(qty)
    order.m_totalQuantity = abs(qty)
    order.m_orderType = 'TRAIL'
    #order.m_lmtPrice = stopPrice
    #order.m_trailStopPrice = stopPrice
    order.m_trailingPercent = trailingPercent

    log.debug('Placing order')
    global _orderId
    # Increment our orderId for next order
    _orderId += 1
    client.placeOrder(_orderId, contract, order)
    time.sleep(0.5)
    print 'disconnected', close_client(client)


# ---------------------------------------------------------------------
# PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio():
    log.info('Getting client')
    client = get_client()
    log.info('Got client, getting portfolio')
    global _portfolio_positions_resp
    _portfolio_positions_resp = dict(positionEnd=False, positions=[])
    client.reqPositions()
    while _portfolio_positions_resp['positionEnd'] is False and client.isConnected() is True:
        log.info("Waiting for responses on {}...".format(client))
        time.sleep(0.5)
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
