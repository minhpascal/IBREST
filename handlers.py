""" Needs documentation
"""
import globals
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.OrderState import OrderState
from app import log

__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# SHARED FUNCTIONS
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSE MESSAGE HANDLERS
# ---------------------------------------------------------------------
def connection_handler(msg):
    """ Handles messages from when we connect to TWS
    """
    if msg.typeName == 'nextValidId':
        globals._orderId = max(int(msg.orderId), globals._orderId)
        log.debug('Connection lock released.  OrderId set to {}'.format(globals._orderId))
        globals._getting_order_id = False  # Unlock place_order() to now be called again.
        log.info('Updated orderID: {}'.format(globals._orderId))
    elif msg.typeName == 'managedAccounts':
        globals._managedAccounts = msg.accountsList.split(',')
        log.info('Updated managed accounts: {}'.format(globals._managedAccounts))


def account_summary_handler(msg):
    """ Update our global Account Summary data response dict
    """
    if msg.typeName == 'accountSummary':
        # account = msg_to_dict(msg)
        globals._account_summary_resp[int(msg.reqId)][msg.tag] = msg.value
    elif msg.typeName == 'accountSummaryEnd':
        globals._account_summary_resp[int(msg.reqId)]['accountSummaryEnd'] = True
    log.debug('SUMMARY: {})'.format(msg))


def account_update_handler(msg):
    """ Update our global Account Update data response dict
    """
    if msg.typeName == 'updateAccountTime':
        globals._account_update_resp[msg.typeName] = msg.updateAccountTime
    elif msg.typeName == 'updateAccountValue':
        account = msg_to_dict(msg)
        globals._account_update_resp[msg.typeName][msg.key] = account
    elif msg.typeName == 'updatePortfolio':
        account = msg_to_dict(msg)
        globals._account_update_resp[msg.typeName].append(account.copy())
    elif msg.typeName == 'accountDownloadEnd':
        globals._account_update_resp[msg.typeName] = True
    log.debug('UPDATE: {})'.format(msg))


def portfolio_positions_handler(msg):
    """ Update our global Portfolio Positoins data response dict
    """
    if msg.typeName == 'position':
        position = msg_to_dict(msg)
        globals._portfolio_positions_resp['positions'].append(position.copy())
    elif msg.typeName == 'positionEnd':
        globals._portfolio_positions_resp['positionEnd'] = True
    log.debug('POSITION: {})'.format(msg))


def history_handler(msg):
    """ Update our global Portfolio Positoins data response dict
    """
    history = msg_to_dict(msg)
    globals._history_resp[int(history['reqId'])] = history.copy()
    log.debug('HISTORY: {})'.format(msg))


def order_handler(msg):
    """ Update our global Order data response dict
    """
    if msg.typeName in ['orderStatus', 'openOrder']:
        d = msg_to_dict(msg)
        globals._order_resp[msg.typeName].append(d.copy())
        globals._order_resp_by_order.get(d['orderId'], dict(openOrder=dict(), orderStatus=dict()))[msg.typeName] = d.copy()
    elif msg.typeName == 'openOrderEnd':
        globals._order_resp['openOrderEnd'] = True
    log.debug('ORDER: {})'.format(msg))


def error_handler(msg):
    """ Update our global to keep the latest errors available for API returns. Error messages have an id attribute which
    maps to the orderId or tickerId of the request which generated the error.
    https://www.interactivebrokers.com/en/software/api/apiguide/java/error.htm

    IbPy provides and id of -1 for connection error messages
    """
    globals._error_resp[int(msg.id)] = {i[0]: i[1] for i in msg.items()}
    log.error('ERROR: {}'.format(msg))


def generic_handler(msg):
    log.debug('MESSAGE: {}, {})'.format(msg, msg.keys))


# ---------------------------------------------------------------------
# FEED MESSAGE HANDLERS
# ---------------------------------------------------------------------
def market_handler(msg):
    """ Update our global Market data response dict
    """
    resp = dict()
    for i in msg.items():
        resp[i[0]] = i[1]
    globals._market_resp.append(resp.copy())