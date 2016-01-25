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



class PortfolioPositions(Resource):
    """ Resource to handle requests for market data
    """

    def get(self):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        return ibrest.get_portfolio()




api.add_resource(Market, '/market/<string:symbol>')
api.add_resource(PortfolioPositions, '/portfolio/positions')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
