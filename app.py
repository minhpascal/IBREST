#!/usr/bin/python
""" IBREST API Flask controller file.  This file establishes the routes used for the IBREST API.  More info at:
https://github.com/hamx0r/IBREST

Most of this API takes HTTP requests and translates them to EClientSocket Methods:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_eclientsocket_methods.htm

The HTTP response is handled by compiling messages from EWrappper Methods into JSON:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_ewrapper_methods.htm
"""
# Flask imports
from flask import Flask
from flask_restful import Resource, Api, reqparse
import ibrest


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
        return ibrest.get_market_data(symbol)


class Orders(Resource):
    """ Resource to handle requests for Orders
    """

    def get(self):
        """ Retrieves details of open orders using reqAllOpenOrders()
        """
        return ibrest.get_open_orders()

    def post(self):
        """ Places an order with placeOrder()
        """
        parser = reqparse.RequestParser()
        parser.add_argument('symbol', type=str, required=True,
                            help='Stock ticker symbol to purchase')
        parser.add_argument('qty', type=int, required=True,
                            help='Total & Minimum Quantity to order (negative for SELL)')
        parser.add_argument('stopPrice', type=int, required=True,
                            help='Stop price (will always sell if lower than this price)')
        parser.add_argument('trailingPercent', type=float, required=True,
                            help='Precentage loss to accept for Trailing Stop Loss order')
        args = parser.parse_args()
        return ibrest.order_trail_stop(args['symbol'], args['qty'], args['stopPrice'], args['trailingPercent'])


    def delete(self):
        """ Cancels order with cancelOrder()
        """
        pass

class PortfolioPositions(Resource):
    """ Resource to handle requests for market data
    """

    def get(self):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        return ibrest.get_portfolio()


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

