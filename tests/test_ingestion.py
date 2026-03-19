from services.data_ingestion.price_service import PriceService
from services.data_ingestion.news_service import NewsService

def test():

    ticker = "AAPL"

    price_service = PriceService()
    news_service = NewsService()

    price = price_service.get_stock_price(ticker)
    news = news_service.get_news(ticker)

    print("\nPRICE DATA:")
    print(price)

    print("\nNEWS DATA:")
    for n in news[:2]:
        print(n)


if __name__ == "__main__":
    test()