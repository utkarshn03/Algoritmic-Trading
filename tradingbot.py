from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from datetime import datetime, timedelta
from alpaca_trade_api import REST
from finbert_utils import estimate_sentiment
import requests

API_KEY = "PKVXR7UHRDX071PGOTUC"
API_SECRET = "2BMWPZewi55n8i8k9l7PCllET96ReovBkOPT09TR"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class TradingBot(Strategy):
    def setup(self, symbol="SPY", risk_factor=0.5):
        self.ticker = symbol
        self.sleep_interval = "24H"
        self.previous_action = None
        self.risk_factor = risk_factor
        self.alpaca_api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def calculate_position(self):
        available_cash = self.get_cash()
        current_price = self.get_last_price(self.ticker)
        shares_to_trade = round(available_cash * self.risk_factor / current_price, 0)
        return available_cash, current_price, shares_to_trade

    def fetch_news(self):
        current_date = self.get_datetime()
        past_date = current_date - timedelta(days=3)
        return self.alpaca_api.get_news(symbol=self.ticker, start=past_date.strftime('%Y-%m-%d'), end=current_date.strftime('%Y-%m-%d'))

    def analyze_sentiment(self):
        news_items = self.fetch_news()
        headlines = [item.__dict__["_raw"]["headline"] for item in news_items]
        sentiment_score, sentiment_label = estimate_sentiment(headlines)
        return sentiment_score, sentiment_label

    def execute_trade(self):
        cash, price, quantity = self.calculate_position()
        sentiment_score, sentiment_label = self.analyze_sentiment()

        if cash > price:
            if sentiment_label == "positive" and sentiment_score > 0.999:
                if self.previous_action == "sell":
                    self.sell_all()
                order = self.create_order(self.ticker, quantity, "buy", take_profit_price=price * 1.20, stop_loss_price=price * 0.95)
                self.submit_order(order)
                self.previous_action = "buy"
            elif sentiment_label == "negative" and sentiment_score > 0.999:
                if self.previous_action == "buy":
                    self.sell_all()
                order = self.create_order(self.ticker, quantity, "sell", take_profit_price=price * 0.8, stop_loss_price=price * 1.05)
                self.submit_order(order)
                self.previous_action = "sell"

if __name__ == "__main__":
    start_date = datetime(2023, 7, 1)
    end_date = datetime(2023, 12, 31)
    broker = Alpaca(ALPACA_CREDS)
    strategy = TradingBot(name='mlstrat', broker=broker, parameters={"symbol": "SPY", "cash_at_risk": 0.5})
    strategy.backtest(YahooDataBacktesting, start_date, end_date, parameters={"symbol": "SPY", "cash_at_risk": 0.5})
