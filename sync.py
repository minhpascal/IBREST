""" Synchronous wrapper on IbPy to do heavy lifting for our Flask app.
This module contains all IB client handling, even if connection will be used for a feed
"""
from connection import get_client, close_client
import globals
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from utils import make_contract
import time
from app import log
from datetime import datetime, timedelta

__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# HISTORY FUNCTIONS
# ---------------------------------------------------------------------
def get_history(args):
    """ Args may be any of those in reqHistoricalData()
    https://www.interactivebrokers.com/en/software/api/apiguide/java/reqhistoricaldata.htm
    """
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]

    # Populate contract with appropriate
    contract = Contract()
    for attr in dir(contract):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(contract, attr, args[attr[2:]])
    contract = make_contract('AAPL')
    globals._tickerId += 1
    globals._history_resp[globals._tickerId] = dict()
    endtime = (datetime.now() - timedelta(minutes=15)).strftime('%Y%m%d %H:%M:%S')
    client.reqHistoricalData(
        tickerId=globals._tickerId,
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
    timeout = globals._timeout
    while len(globals._history_resp[globals._tickerId]) == 0 and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        if globals._error_resp.get(globals._tickerId, None) is not None:
            close_client(client)
            return globals._error_resp[globals._tickerId]
        elif client.isConnected() is False:
            return {'errorMsg': 'Connection lost'}
        time.sleep(0.25)
        timeout -= 1
    log.debug('histor: {}'.format(globals._history_resp))
    resp = globals._history_resp[globals._tickerId].copy()
    client.cancelHistoricalData(globals._tickerId)
    close_client(client)
    return resp


# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_open_orders():
    """ Uses reqAllOpenOrders to get all open orders from 
    """
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]

    # Reset our order resp to prepare for new data
    globals._order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
    client.reqAllOpenOrders()
    timeout = globals._timeout
    while globals._order_resp['openOrderEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    return globals._order_resp


def cancel_order(orderId):
    """ Uses cancelOrder to cancel an order.  The only response is what comes back right away (no EWrapper messages)
    """
    globals._error_resp[orderId] = None  # Reset our error for later

    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]

    log.info('Cancelling order {}'.format(orderId))
    # Reset our order resp to prepare for new data
    globals._order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    client.cancelOrder(int(orderId))
    timeout = globals._timeout
    while len(globals._order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        if globals._error_resp[orderId] is not None:
            close_client(client)
            return globals._error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    resp = globals._order_resp.copy()
    # Cancelling an order also produces an error, we'll capture that here too
    resp['error'] = globals._error_resp[orderId]
    return resp


def place_order(args):
    """ Auto-detects which args should be assigned to a new Contract or Order, then use to place order.
    Makes use of globals to set initial values, but allows args to override (ie clientId)
    """
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]

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
    # Get our next valid order ID
    if args.get('orderId', None) is None:
        globals._getting_order_id = True
        client.reqIds(1)
        timeout = globals._timeout
        while globals._getting_order_id is True and timeout > 0:
            log.debug('Waiting for new orderId')
            time.sleep(0.25)
            timeout -= 1

        orderId = globals._orderId
    else:
        orderId = args.get('orderId')
    globals._error_resp[orderId] = None
    # Reset our order resp to prepare for new data
    globals._order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    log.debug('Placing order # {}'.format(orderId))
    client.placeOrder(orderId, contract, order)

    # client.reqOpenOrders()
    timeout = 8
    # while len(_order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
    while client.isConnected() is True and timeout > 0:
        log.info("Waiting for orderId {} responses on client {}...".format(orderId, client.clientId))
        if globals._error_resp[orderId] is not None:
            close_client(client)
            return globals._error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1

    close_client(client)
    return {'status': 'OK'}


# ---------------------------------------------------------------------
# PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio_positions():
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]
    globals._portfolio_positions_resp = dict(positionEnd=False, positions=[])
    client.reqPositions()
    timeout = globals._timeout
    while globals._portfolio_positions_resp['positionEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    client.cancelPositions()
    close_client(client)
    return globals._portfolio_positions_resp


def get_account_summary(tags):
    """ Calls reqAccountSummary() then listens for accountSummary messages()
    """
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]
    client_id = client.clientId
    globals._account_summary_resp[client_id] = dict(accountSummaryEnd=False)
    client.reqAccountSummary(client_id, 'All', tags)
    timeout = globals._timeout
    while globals._account_summary_resp[client_id][
        'accountSummaryEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    # time.sleep(1)
    client.cancelAccountSummary(client_id)
    close_client(client)
    return globals._account_summary_resp[client_id]


def get_account_update(acctCode):
    """ Calls reqAccountUpdates(subscribe=False) then listens for accountAccountTime/AccountValue/Portfolio messages
    """
    client = get_client()
    if client is None or client.isConnected() is False:
        return globals._error_resp[-1]
    client_id = client.clientId
    globals._account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
    log.debug('Requsting account updates for {}'.format(acctCode))
    client.reqAccountUpdates(subscribe=False, acctCode=acctCode)
    timeout = globals._timeout
    while globals._account_update_resp['accountDownloadEnd'] is False and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(.25)
        timeout -= 1
        log.debug('Current update {}'.format(globals._account_update_resp))
    client.cancelAccountSummary(client_id)
    close_client(client)
    return globals._account_update_resp