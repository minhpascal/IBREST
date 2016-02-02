""" Synchronous wrapper on IbPy to do heavy lifting for our Flask app.
This module contains all IB client handling, even if connection will be used for a feed
"""
from ib.opt import ibConnection
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.OrderState import OrderState
from flask import current_app
import time
from app import app
from feeds import market_handler
import os
from datetime import datetime, timedelta

__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# GLOBAL PARAMETERS
# ---------------------------------------------------------------------
# Configuration
# Use environment variables
_ibgw_host = os.getenv('IBGW_HOST', '127.0.0.1')
_ibgw_port = int(os.getenv('IBGW_PORT', '4001'))  # Use 7496 for TWS
_timeout = 20  # Max loops

# Mutables
_managedAccounts = []
_clientId_pool = {0, 1, 2, 3, 4, 5, 6, 7}
_connection_in_progress = False
_orderId = 0
_tickerId = 0

# Responses.  Global dicts to use for our responses as updated by Message handlers, keyed by clientId
_portfolio_positions_resp = {c: dict() for c in xrange(8)}
_account_summary_resp = {c: dict(accountSummaryEnd=False) for c in xrange(8)}
_account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
# Track errors keyed in "id" which is the orderId or tickerId (or -1 for connection errors)
_error_resp = dict()
# When getting order info, we want it for all clients, and don't care so much if multiple requests try to populate this
_order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
# When placing/deleting orders, we care about what orderId is used.  Key off orderId.
_order_resp_by_order = dict()
# Dict of history responses keyed off of reqId (tickerId)
_history_resp = dict()

# Logging shortcut
log = app.logger


# ---------------------------------------------------------------------
# MESSAGE HANDLERS
# ---------------------------------------------------------------------
def connection_handler(msg):
    """ Handles messages from when we connect to TWS
    """
    if msg.typeName == 'nextValidId':
        global _orderId, _connection_in_progress
        _orderId = max(int(msg.orderId), _orderId)
        log.debug('Connection lock released.  OrderId set to {}'.format(_orderId))
        _connection_in_progress = False  # Unlock get_client() to now be called again.
        log.info('Updated orderID: {}'.format(_orderId))
    elif msg.typeName == 'managedAccounts':
        global _managedAccounts
        _managedAccounts = msg.accountsList.split(',')
        log.info('Updated managed accounts: {}'.format(_managedAccounts))


def account_summary_handler(msg):
    """ Update our global Account Summary data response dict
    """

    if msg.typeName == 'accountSummary':
        #account = msg_to_dict(msg)
        _account_summary_resp[int(msg.reqId)][msg.tag] = msg.value
    elif msg.typeName == 'accountSummaryEnd':
        _account_summary_resp[int(msg.reqId)]['accountSummaryEnd'] = True
    log.debug('SUMMARY: {})'.format(msg))


def account_update_handler(msg):
    """ Update our global Account Update data response dict
    """
    global _account_update_resp
    if msg.typeName == 'updateAccountTime':
        _account_update_resp[msg.typeName] = msg.updateAccountTime
    elif msg.typeName == 'updateAccountValue':
        account = msg_to_dict(msg)
        _account_update_resp[msg.typeName][msg.key] = account
    elif msg.typeName == 'updatePortfolio':
        account = msg_to_dict(msg)
        _account_update_resp[msg.typeName].append(account.copy())
    elif msg.typeName == 'accountDownloadEnd':
        _account_update_resp[msg.typeName] = True
    log.debug('UPDATE: {})'.format(msg))

def portfolio_positions_handler(msg):
    """ Update our global Portfolio Positoins data response dict
    """
    if msg.typeName == 'position':
        position = msg_to_dict(msg)
        _portfolio_positions_resp['positions'].append(position.copy())
    elif msg.typeName == 'positionEnd':
        _portfolio_positions_resp['positionEnd'] = True
    log.debug('POSITION: {})'.format(msg))


def history_handler(msg):
    """ Update our global Portfolio Positoins data response dict
    """
    global _history_resp
    history = msg_to_dict(msg)
    _history_resp[int(history['reqId'])] = history.copy()
    log.debug('HISTORY: {})'.format(msg))


def order_handler(msg):
    """ Update our global Order data response dict
    """
    global _order_resp, _order_resp_by_order, _orderId
    if msg.typeName in ['orderStatus', 'openOrder']:
        d = msg_to_dict(msg)
        _order_resp[msg.typeName].append(d.copy())
        _order_resp_by_order.get(d['orderId'], dict(openOrder=dict(), orderStatus=dict()))[msg.typeName] = d.copy()
        # Different clientIds get tied to different orderIds, but we should always track the max
        _orderId = max(_orderId, msg.orderId+1)
        log.info('Updated orderID: {}'.format(_orderId))
    elif msg.typeName == 'openOrderEnd':
        _order_resp['openOrderEnd'] = True
    log.debug('ORDER: {})'.format(msg))


def error_handler(msg):
    """ Update our global to keep the latest errors available for API returns. Error messages have an id attribute which
    maps to the orderId or tickerId of the request which generated the error.
    https://www.interactivebrokers.com/en/software/api/apiguide/java/error.htm

    IbPy provides and id of -1 for connection error messages
    """
    global _error_resp
    _error_resp[int(msg.id)] = {i[0]: i[1] for i in msg.items()}
    log.error('ERROR: {}'.format(msg))


def generic_handler(msg):
    log.debug('MESSAGE: {}, {})'.format(msg, msg.keys))


# ---------------------------------------------------------------------
# SHARED FUNCTIONS
# ---------------------------------------------------------------------
def get_client(client_id=None):
    """ Creates a client connection to be used with orders
    """
    global _connection_in_progress

    if client_id is None:
        # Get client ID from our pool list in memory
        timeout = _timeout
        while len(_clientId_pool) == 0 and timeout > 0:
            time.sleep(0.5)
            timeout -= 1
        try:
            client_id = _clientId_pool.pop()
        except KeyError:
            client_id = None
    if client_id is None:
        return

    # Ensure some other call to this function is not working at the same time.  Due to Order messages which may flood
    # when connecting, we need a way to ensure only one connecting is in the process of being made at a time.
    timeout = _timeout
    while _connection_in_progress is True and timeout > 0:
        time.sleep(0.5)
        timeout -= 1
    log.info('Attempting connection with client_id {}'.format(client_id))
    # TODO: Instead of using a lock, shift onus to order() functions to use reqIDs()
    _connection_in_progress = True  # NextValidId message will clear this for us.
    client = ibConnection(_ibgw_host, _ibgw_port, client_id)

    # Add synchronous response handlers
    client.register(connection_handler, 'ManagedAccounts', 'NextValidId')
    client.register(history_handler, 'HistoricalData')
    client.register(order_handler, 'OpenOrder', 'OrderStatus', 'OpenOrderEnd')
    client.register(portfolio_positions_handler, 'Position', 'PositionEnd')
    client.register(account_summary_handler, 'AccountSummary', 'AccountSummaryEnd')
    client.register(account_update_handler, 'UpdateAccountTime', 'UpdateAccountValue', 'UpdatePortfolio',
                    'AccountDownloadEnd')
    client.register(error_handler, 'Error')
    # Add handlers for feeds
    client.register(market_handler, 'TickSize', 'TickPrice')
    # Enable logging if we're in debug mode
    #if current_app.debug is True:
        #client.registerAll(generic_handler)
        #client.enableLogging()
    client.connect()

    # Wait a bit to ensure we got messages back confirming we're connected and _order_id is updated.
    timeout = _timeout
    while client.isConnected() is False and timeout > 0:
        time.sleep(0.25)
        timeout -= 1
    log.debug('Waiting for messages to settle...')
    time.sleep(2)
    log.debug('Returning client...')
    return client


def close_client(client):
    """ Put clientId back into pool and close connection
    """
    client_id = client.clientId
    # Add our client_id back into our pool
    _clientId_pool.add(client_id)

    # Now close our actual client
    client.close()
    return client_id


def msg_to_dict(msg):
    """ Converts a message to a dict
    """
    d = dict()
    for i in msg.items():
        if isinstance(i[1], (Contract, Order, OrderState)):
            d[i[0]] = i[1].__dict__
        else:
            d[i[0]] = i[1]
    return d


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
# HISTORY FUNCTIONS
# ---------------------------------------------------------------------
def get_history(args):
    """ Args may be any of those in reqHistoricalData()
    https://www.interactivebrokers.com/en/software/api/apiguide/java/reqhistoricaldata.htm
    """
    client = get_client()

    # Populate contract with appropriate
    contract = Contract()
    for attr in dir(contract):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(contract, attr, args[attr[2:]])
    contract = make_contract('AAPL')
    global _tickerId, _history_resp
    _tickerId += 1
    _history_resp[_tickerId] = dict()
    endtime = (datetime.now() - timedelta(minutes=15)).strftime('%Y%m%d %H:%M:%S')
    client.reqHistoricalData(
            tickerId=_tickerId,
            contract=contract,
            endDateTime=endtime,
            durationStr='2 D',
            barSizeSetting='30 mins',
            whatToShow='TRADES',
            useRTH=0,
            formatDate=1)

    """
    durationStr='60 S',
    barSizeSetting='1 min',
    whatToShow='TRADES',
    useRTH=0,
    formatDate=1)
    """
    timeout = _timeout
    while len(_history_resp[_tickerId]) == 0 and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        if _error_resp.get(_tickerId, None) is not None:
            close_client(client)
            return _error_resp[_tickerId]
        elif client.isConnected() is False:
            return {'errorMsg': 'Connection lost'}
        time.sleep(0.25)
        timeout -= 1
    log.debug('histor: {}'.format(_history_resp))
    resp = _history_resp[_tickerId].copy()
    client.cancelHistoricalData(_tickerId)
    close_client(client)
    return resp


# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_open_orders():
    """ Uses reqAllOpenOrders to get all open orders from 
    """
    global _order_resp
    client = get_client()
    if client is None or client.isConnected() is False:
        global _error_resp
        return _error_resp[-1]

    # Reset our order resp to prepare for new data
    _order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
    client.reqAllOpenOrders()
    timeout = _timeout
    while _order_resp['openOrderEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    return _order_resp


def cancel_order(orderId):
    """ Uses cancelOrder to cancel an order.  The only response is what comes back right away (no EWrapper messages)
    """
    global _order_resp_by_order
    global _error_resp
    _error_resp[orderId] = None  # Reset our error for later

    client = get_client()
    log.info('Cancelling order {}'.format(orderId))
    # Reset our order resp to prepare for new data
    _order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    client.cancelOrder(int(orderId))
    timeout = _timeout
    while len(_order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        if _error_resp[orderId] is not None:
            close_client(client)
            return _error_resp[_orderId]
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    resp = _order_resp.copy()
    # Cancelling an order also produces an error, we'll capture that here too
    resp['error'] = _error_resp[_orderId]
    return resp


def place_order(args):
    """ Auto-detects which args should be assigned to a new Contract or Order, then use to place order.
    Makes use of globals to set initial values, but allows args to override (ie clientId)
    """
    client = get_client()

    # Populate contract with appropriate
    contract = Contract()
    for attr in dir(contract):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(contract, attr, args[attr[2:]])

    # Populate order with appropriate
    order = Order()
    order.m_clientId = client.clientId
    for attr in dir(order):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(order, attr, args[attr[2:]])
    log.debug('Contract: {}, Order: {}'.format(contract.__dict__, order.__dict__))
    # correct next orderId when we go to place our order.
    global _orderId
    orderId = args.get('orderId', None) or _orderId
    global _order_resp_by_order
    global _error_resp
    _error_resp[orderId] = None
    # Reset our order resp to prepare for new data
    _order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    log.debug('Placing order # {}'.format(orderId))
    client.placeOrder(orderId, contract, order)

    #client.reqOpenOrders()
    timeout = 8
    #while len(_order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
    while client.isConnected() is True and timeout > 0:
        log.info("Waiting for orderId {} responses on client {}...".format(orderId, client.clientId))
        if _error_resp[orderId] is not None:
            close_client(client)
            return _error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1


    close_client(client)
    return {'status': 'OK'}


# ---------------------------------------------------------------------
# PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio_positions():
    client = get_client()
    global _portfolio_positions_resp
    _portfolio_positions_resp = dict(positionEnd=False, positions=[])
    client.reqPositions()
    timeout = _timeout
    while _portfolio_positions_resp['positionEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    client.cancelPositions()
    close_client(client)
    return _portfolio_positions_resp


def get_account_summary(tags):
    """ Calls reqAccountSummary() then listens for accountSummary messages()
    """
    client = get_client()
    client_id = client.clientId
    global _account_summary_resp
    _account_summary_resp[client_id] = dict(accountSummaryEnd=False)
    client.reqAccountSummary(client_id, 'All', tags)
    timeout = _timeout
    while _account_summary_resp[client_id]['accountSummaryEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    #time.sleep(1)
    client.cancelAccountSummary(client_id)
    close_client(client)
    return _account_summary_resp[client_id]


def get_account_update(acctCode):
    """ Calls reqAccountUpdates(subscribe=False) then listens for accountAccountTime/AccountValue/Portfolio messages
    """
    client = get_client()
    client_id = client.clientId
    global _account_update_resp
    _account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
    log.debug('Requsting account updates for {}'.format(acctCode))
    client.reqAccountUpdates(subscribe=False, acctCode=acctCode)
    timeout = _timeout
    while _account_update_resp['accountDownloadEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(.25)
        timeout -= 1
        log.debug('Current update {}'.format(_account_update_resp))
    client.cancelAccountSummary(client_id)
    close_client(client)
    return _account_update_resp


