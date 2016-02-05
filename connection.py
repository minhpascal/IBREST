""" Needs documentation
"""
import time
# from app import log
import logging
import globals as g
import utils
from handlers import connection_handler, history_handler, order_handler, portfolio_positions_handler, \
    account_summary_handler, account_update_handler, error_handler, market_handler
from flask import current_app

__author__ = 'Jason Haury'

log = logging.getLogger(__name__)
log = utils.setup_logger(log)



def get_client(client_id=None):
    """ Creates a client connection to be used with orders
    """
    if client_id is None:
        # Get client ID from our pool list in memory
        log.debug('Current clients available: {}'.format(g.clientId_pool))
        timeout = g.timeout
        while len(g.clientId_pool) == 0 and timeout > 0:
            log.debug('Waiting for clientId to become available...({})'.format(timeout))
            time.sleep(0.5)
            timeout -= 1
        try:
            client_id = g.clientId_pool.pop(0)
        except IndexError:
            client_id = None
    else:
        # A client ID was specified, so wait for it to become available if it's not already
        # First, make sure our client_id is valid
        if client_id not in range(8):
            return
        if client_id in g.clientId_pool:
            g.clientId_pool.pop(g.clientId_pool.index(client_id))

    if client_id is None:
        return

    log.debug('Attempting connection with client_id {}'.format(client_id))
    client = g.client_pool[client_id]

    # Enable logging if we're in debug mode
    if current_app.debug is True:
        client.enableLogging()

    # Reconnect if needed
    if not client.isConnected():
        client.connect()
    return client

    """
    # Wait a bit to ensure we got messages back confirming we're connected and _order_id is updated.
    timeout = timeout
    while client.isConnected() is False and timeout > 0:
        time.sleep(0.25)
        timeout -= 1
    log.debug('Waiting for messages to settle...')

    log.debug('Returning client...')
    return client
    """


def setup_client(client):
    """ Attach handlers to the clients
    """
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


def close_client(client):
    """ Put clientId back into pool but don't close connection
    """
    if client is None:
        return
    client_id = client.clientId
    # Add our client_id onto end of our pool
    g.clientId_pool.append(client_id)
    return client_id
