from time import time, mktime
import datetime
from functools import reduce
from math import floor
import requests
import calendar
import psycopg2

conn = psycopg2.connect("dbname=main user=postgres password=Password1 host=35.188.228.208")
cur = conn.cursor()

def getResults(ticker, mod, offset, start):
    cur.execute("SELECT * FROM historical WHERE ticker = %s AND MOD((EXTRACT(EPOCH FROM date)::int / 86400) - 4, %s) = %s AND date >= %s::date", (ticker, mod, offset, datetime.datetime.fromtimestamp(start * 86400).strftime('%Y-%m-%d')))
    return cur.fetchall()

def loadData(ticker):
    cur.execute("SELECT date FROM historical WHERE ticker = %s ORDER BY date DESC LIMIT 1", (ticker,))
    lastFetched = cur.fetchone()
    data = requests.get('https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol='+ticker+'&outputsize='+("compact" if (lastFetched != None and (datetime.date.today() - lastFetched[0]).days < 100) else "full")+'&apikey=M8JYXOYYMPLVY09N').json()["Time Series (Daily)"]
    values = ""
    for key, item in data.items():
        close = item['4. close']
        if (values != ""):
            values += ","
        values+="('"+ticker+"','"+key+"','$"+close+"')"

    cur.execute("INSERT INTO historical (ticker, date, close) VALUES " + values)
    conn.commit()

def query(ticker, interval):
    mod = {
        "1w": 1,
        "1m": 7,
        "1y": 14
    }
    
    today = (floor(time() / 86400) - 1)

    offset = (datetime.datetime.today().weekday() + 6) % mod[interval]

    if offset == 7 or offset == 6:
        offset = 5

    count = {
        "1w": 9,
        "1m": 4,
        "1y": 24
    }[interval]

    expectedCount = count

    weekday = datetime.datetime.today().weekday() + 6 + count * mod[interval]
    
    for i in range(0, count):
        if weekday % 6 == 0 or weekday % 7 == 0:
             expectedCount -= 1
        weekday -= 1
    
    start = today - count * mod[interval]

    results = getResults(ticker, mod[interval], offset, start)

    if len(results) < expectedCount:
        loadData(ticker)
        results = getResults(ticker, mod[interval], offset, start)
    
    resultsMap = {}

    for result in results:
        resultsMap[floor(mktime(result[2].timetuple()) / 86400)] = result

    output = []

    for i in range(0, count):
        day = today - 1 - i * mod[interval]
        if day in resultsMap:
            output.append(resultsMap[day])

    return output


from flask import Flask
from flask_restful import Resource, Api, reqparse
import json

parser = reqparse.RequestParser()
parser.add_argument('ticker', type=str, help='Ticker to acquire time series data for', required=True)
parser.add_argument('interval', type=str, help='How long to look back. Currently only 1w, 1m, or 1y.', required=True)

parser_search = reqparse.RequestParser()
parser_search.add_argument('query', type=str, help='Search query to look for tickers with.', required=True)

app = Flask(__name__)
api = Api(app)

def date_handler(x):
    if isinstance(x, datetime.date):
        return x.isoformat()
    raise TypeError("Unknown type")

class TickerData(Resource):
    def get(self):
        args = parser.parse_args()
        print('TickerData', args['ticker'], args['interval'])
        result = query(args['ticker'], args['interval'])
        return [{'ticker': str(a[1]), 'date': str(a[2].isoformat()), 'price': str(a[3])} for a in result]

api.add_resource(TickerData, '/data')


import pickle
from collections import defaultdict
def dddd():
    return 0
def dd():
    return defaultdict(dddd)
bows, index = pickle.load(open("searchfile.pickle", "rb"))
symbols = pickle.load(open("symbols.pickle", "rb"))
import math

def search(searchterm):
    number_of_terms_that_match = {symbol: 0 for symbol, fullname in symbols.items()}
    if searchterm.upper() in symbols:
        number_of_terms_that_match[searchterm.upper()] += 100000000
    for term in searchterm.lower().split(' '):
        for ticker in index[term]:
            number_of_terms_that_match[ticker] += math.log(len(bows) / len(index[term])) * index[term][ticker] / sum(bows[ticker].values())
    return [s for s, val in sorted(number_of_terms_that_match.items(),key=lambda x:-x[1]) if val > 0][:10]

class SearchQuery(Resource):
    def get(self):
        args = parser_search.parse_args()
        print('SearchQuery', args['query'])
        return search(args['query'])

api.add_resource(SearchQuery, '/search')

if __name__ == '__main__':
    app.run(debug=True)

#cur.close()
#conn.close()
