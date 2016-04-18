""" Synchronous wrapper on IbPy to do heavy lifting for our Flask app.
This module contains all IB client handling, even if connection will be used for a feed
"""
import globals as g
from connection import get_client, close_client

# from flask import g
from ib.ext.Contract import Contract
from ib.ext.Order import Order
import utils
import time
import logging
from datetime import datetime, timedelta

__author__ = 'Jason Haury'

log = logging.getLogger(__name__)
log = utils.setup_logger(log)


# ---------------------------------------------------------------------
# HISTORY FUNCTIONS
# ---------------------------------------------------------------------
def get_history(args):
    """ Args may be any of those in reqHistoricalData()
    https://www.interactivebrokers.com/en/software/api/apiguide/java/reqhistoricaldata.htm
    """
    # TODO complete this endpoint
    client = get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # Populate contract with appropriate
    contract = Contract()
    for attr in dir(contract):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(contract, attr, args[attr[2:]])
    contract = utils.make_contract('AAPL')
    g.tickerId += 1
    g.history_resp[g.tickerId] = dict()
    endtime = (datetime.now() - timedelta(minutes=15)).strftime('%Y%m%d %H:%M:%S')
    client.reqHistoricalData(
        tickerId=g.tickerId,
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
    timeout = g.timeout
    while len(g.history_resp[g.tickerId]) == 0 and timeout > 0:
        log.debug("Waiting for History responses on client {}...".format(client.clientId))
        if g.error_resp.get(g.tickerId, None) is not None:
            close_client(client)
            return g.error_resp[g.tickerId]
        elif client.isConnected() is False:
            return {'errorMsg': 'Connection lost'}
        time.sleep(0.25)
        timeout -= 1
    log.debug('histor: {}'.format(g.history_resp))
    resp = g.history_resp[g.tickerId].copy()
    client.cancelHistoricalData(g.tickerId)
    close_client(client)
    return resp


# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_open_orders():
    """ Uses reqAllOpenOrders to get all open orders from 
    """
    client = get_client(0)
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # Reset our order resp to prepare for new data
    g.order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
    client.reqAllOpenOrders()
    timeout = g.timeout
    while g.order_resp['openOrderEnd'] is False and client.isConnected() is True and timeout > 0:
        log.debug("Waiting for Open Orders responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    return g.order_resp


def cancel_order(orderId):
    """ Uses cancelOrder to cancel an order.  The only response is what comes back right away (no EWrapper messages)
    """
    g.error_resp[orderId] = None  # Reset our error for later

    client = get_client(0)
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    log.info('Cancelling order {}'.format(orderId))
    # Reset our order resp to prepare for new data
    g.order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    client.cancelOrder(int(orderId))
    timeout = g.timeout
    while len(g.order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
        log.debug("Waiting for Cancel Order responses on client {}...".format(client.clientId))
        if g.error_resp[orderId] is not None:
            close_client(client)
            return g.error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1
    close_client(client)
    resp = g.order_resp.copy()
    # Cancelling an order also produces an error, we'll capture that here too
    resp['error'] = g.error_resp[orderId]
    return resp


def place_order(args):
    """ Auto-detects which args should be assigned to a new Contract or Order, then use to place order.
    Makes use of globals to set initial values, but allows args to override (ie clientId)

    To modify and order, the following parameters are needed (IB won't complain if some of these are missing, but the
    order update won't succeed):
    * orderId
    * exchange
    * totalQuantity
    * secType
    * action
    * orderType AND related paramters (ie TRAIL needs trailingPercent)
    * symbol
    * currency
    * exchange
    """
    log.debug('Starting place_order with args: {}'.format(args))
    # TODO do we need client 0 if we're modifying an order?
    client = get_client(0)
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # If an orderId was provided, we'll be updating an existing order, so only send attributes which are updatable:
    # totalQuantity, orderType, symbol, secType, action

    # TODO which implementation?
    #orderId = args.get('orderId', orderId=g.orderId)

    orderId = args.get('orderId', None)
    if orderId is None:
        '''
        # Get our next valid order ID
        g.getting_order_id = True
        client.reqIds(1)
        # TODO call get open orders and look for orderId to be in a particular state or get an error, minimize waiting
        timeout = g.timeout
        while g.getting_order_id is True and timeout > 0:
            log.debug('Waiting for new orderId {} more times...'.format(timeout))
            time.sleep(0.25)
            timeout -= 1
        orderId = g.orderId
        '''
        orderId = g.orderId
        g.orderId += 1
    contract = Contract()
    order = Order()

    # Populate contract with appropriate args
    for attr in dir(contract):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(contract, attr, args[attr[2:]])
    # Populate order with appropriate
    order.m_clientId = client.clientId
    for attr in dir(order):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(order, attr, args[attr[2:]])

    # Reset our order resp to prepare for new data
    g.order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    g.error_resp[orderId] = None  # Reset our error for later
    log.debug(
        'Placing order # {} on client # {} (connected={}) '.format(orderId, client.clientId, client.isConnected()))
    client.placeOrder(orderId, contract, order)
    # The only response for placing an order is an error, so we'll check for open orders and wait for this orderId or
    # and error to show up.

    client.reqOpenOrders()
    timeout = g.timeout
    while len(g.order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
        log.debug("Waiting for orderId {} responses for {} more times...".format(orderId, timeout))
        if g.error_resp[orderId] is not None:
            close_client(client)
            return g.error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1

    close_client(client)
    return g.order_resp_by_order[orderId]


# ---------------------------------------------------------------------
# ACCOUNT & PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio_positions():
    client = get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    g.portfolio_positions_resp = dict(positionEnd=False, positions=[])
    client.reqPositions()
    timeout = g.timeout
    while g.portfolio_positions_resp['positionEnd'] is False and client.isConnected() is True and timeout > 0:
        log.debug("Waiting for Portfolio Positions responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    client.cancelPositions()
    close_client(client)
    return g.portfolio_positions_resp


def get_account_summary(tags):
    """ Calls reqAccountSummary() then listens for accountSummary messages()
    """
    client = get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    client_id = client.clientId
    g.account_summary_resp[client_id] = dict(accountSummaryEnd=False)
    client.reqAccountSummary(client_id, 'All', tags)
    timeout = g.timeout
    while g.account_summary_resp[client_id]['accountSummaryEnd'] is False \
            and client.isConnected() is True \
            and timeout > 0:
        log.debug("Waiting for Account Summary responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    # time.sleep(1)
    client.cancelAccountSummary(client_id)
    close_client(client)
    return g.account_summary_resp[client_id]


def get_account_update(acctCode):
    """ Calls reqAccountUpdates(subscribe=False) then listens for accountAccountTime/AccountValue/Portfolio messages
    """
    client = get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    client_id = client.clientId
    g.account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
    log.debug('Requsting account updates for {}'.format(acctCode))
    client.reqAccountUpdates(subscribe=False, acctCode=acctCode)
    timeout = g.timeout
    while g.account_update_resp['accountDownloadEnd'] is False and client.isConnected() is True and timeout > 0:
        log.debug("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(.25)
        timeout -= 1
        log.debug('Current update {}'.format(g.account_update_resp))
    client.cancelAccountSummary(client_id)
    close_client(client)
    return g.account_update_resp