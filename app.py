#!/usr/bin/python
""" IBREST API Flask app controller file.  This file establishes the routes used for the IBREST API.  More info at:
https://github.com/hamx0r/IBREST

Most of this API takes HTTP requests and translates them to EClientSocket Methods:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_eclientsocket_methods.htm

The HTTP response is handled by compiling messages from EWrappper Methods into JSON:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_ewrapper_methods.htm
"""
# Flask imports
from flask import Flask, request
from flask_restful import Resource, Api, reqparse
# IBREST imports
import sync

__author__ = 'Jason Haury'

app = Flask(__name__)
api = Api(app)


# ---------------------------------------------------------------------
# RESOURCES
# ---------------------------------------------------------------------
class Market(Resource):
    """ Resource to handle requests for market data
    """
    def get(self, symbol):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        # TODO add query string params for other Contract
        '''
        parser = reqparse.RequestParser()
        parser.add_argument('rate', type=int, help='Rate to charge for this resource')
        args = parser.parse_args()
        '''
        return sync.get_market_data(symbol)


class Orders(Resource):
    """ Resource to handle requests for Orders
    """

    def get(self):
        """ Retrieves details of open orders using reqAllOpenOrders()
        """
        return sync.get_open_orders()

    def post(self):
        """ Places an order with placeOrder().  This requires enough args to create a Contract & and Order:
        https://www.interactivebrokers.com/en/software/api/apiguide/java/java_socketclient_properties.htm
        """
        parser = reqparse.RequestParser()
        # Contract args https://www.interactivebrokers.com/en/software/api/apiguide/java/contract.htm
        parser.add_argument('orderType', type=str, required=True,
                            help='Type of Order to place', choices=['LMT', 'MTL', 'MKT PRT', 'QUOTE', 'STP', 'STP LMT',
                                                                    'TRAIL LIT', 'TRAIL MIT', 'TRAIL', 'TRAIL LIMIT',
                                                                    'MKT', 'MIT', 'MOC', 'MOO', 'PEG MKT', 'REL',
                                                                    'BOX TOP', 'LOC', 'LOO', 'LIT', 'PEG MID', 'VWAP',
                                                                    'GAT', 'GTD', 'GTC', 'IOC', 'OCA', 'VOL'])
        parser.add_argument('secType', type=str, required=False, default='STK',
                            help='Security Type', choices=['STK', 'OPT', 'FUT', 'IND', 'FOP', 'CASH', 'BAG', 'NEWS'])
        parser.add_argument('exchange', type=str, required=False, default='SMART',
                            help='Exchange (ie NASDAQ, SMART)')
        parser.add_argument('currency', type=str, required=False, default='USD',
                            help='Currency used for order (ie USD, GBP))')
        parser.add_argument('symbol', type=str, required=True,
                            help='Stock ticker symbol to order')

        # Order args https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
        # Order types https://www.interactivebrokers.com/en/software/api/apiguide/tables/supported_order_types.htm
        parser.add_argument('totalQuantity', type=int, required=True,
                            help='Total Quantity to order')
        parser.add_argument('action', type=str, required=True,
                            help='Must be BUY, SELL or SSHORT')
        parser.add_argument('tif', type=str, required=False,
                            help='Time in force', choices=['DAT', 'GTC', 'IOC', 'GTD'])

        '''
        parser.add_argument('stopPrice', type=int, required=True,
                            help='Stop price (will always sell if lower than this price)')
        parser.add_argument('trailingPercent', type=float,
                            help='Precentage loss to accept for Trailing Stop Loss order')
        '''
        args = parser.parse_args()
        all_args = request.args.copy()
        for k, v in args.iteritems():
            all_args[k] = v
        print all_args
        return sync.place_order(args)

    def delete(self):
        """ Cancels order with cancelOrder()
        """
        parser = reqparse.RequestParser()
        parser.add_argument('orderId', type=int, required=True,
                            help='Order ID to cancel')
        args = parser.parse_args()
        return sync.cancel_order(args['orderId'])


class PortfolioPositions(Resource):
    """ Resource to handle requests for market data
    """

    def get(self):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        return sync.get_portfolio()


# ---------------------------------------------------------------------
# ROUTING
# ---------------------------------------------------------------------
api.add_resource(Market, '/market/<string:symbol>')
api.add_resource(Orders, '/order')
api.add_resource(PortfolioPositions, '/portfolio/positions')

if __name__ == '__main__':
    import os
    host = os.getenv('IBREST_HOST', '127.0.0.1')
    port = int(os.getenv('IBREST_PORT', '5000'))
    app.run(debug=True, host=host, port=port)

