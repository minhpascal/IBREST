""" Needs documentation
"""
from flask import current_app
import globals as g
from handlers import connection_handler, history_handler, order_handler, portfolio_positions_handler, \
    account_summary_handler, account_update_handler, error_handler, market_handler
from ib.opt import ibConnection
import logging
import os
import utils


__author__ = 'Jason Haury'
log = logging.getLogger(__name__)
log = utils.setup_logger(log)


def get_client():
    """ Gets the global client and ensures it's still connected
    """
    #log.debug('Attempting connection with client_id {}'.format(clientId))
    # Reconnect if needed
    if not hasattr(g.client, 'isConnected') or not g.client.isConnected():

        if current_app.debug is True:
            g.client.enableLogging()
        # Enable logging if we're in debug mode
        g.client.register(connection_handler, 'ManagedAccounts', 'NextValidId')
        g.client.register(history_handler, 'HistoricalData')
        g.client.register(order_handler, 'OpenOrder', 'OrderStatus', 'OpenOrderEnd')
        g.client.register(portfolio_positions_handler, 'Position', 'PositionEnd')
        g.client.register(account_summary_handler, 'AccountSummary', 'AccountSummaryEnd')
        g.client.register(account_update_handler, 'UpdateAccountTime', 'UpdateAccountValue', 'UpdatePortfolio',
                        'AccountDownloadEnd')
        g.client.register(error_handler, 'Error')
        # Add handlers for feeds
        g.client.register(market_handler, 'TickSize', 'TickPrice')
        g.client.connect()

    return g.client