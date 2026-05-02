import numpy as np
import yfinance as yf
import requests
from django.core.cache import cache 
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 

class InvestmentAHP:
    STOCK_CATALOG = {
        '🔥 Топ Світу': [
            {'t': 'AAPL', 'n': 'Apple'}, {'t': 'MSFT', 'n': 'Microsoft'},
            {'t': 'NVDA', 'n': 'NVIDIA'}, {'t': 'AMZN', 'n': 'Amazon'},
            {'t': 'GOOGL', 'n': 'Google'}
        ],
        '🚗 Автомобілі': [
            {'t': 'TSLA', 'n': 'Tesla (Електро)'}, {'t': 'TM', 'n': 'Toyota (Надійність)'},
            {'t': 'F', 'n': 'Ford'}, {'t': 'RACE', 'n': 'Ferrari'}
        ],
        '🍔 Їжа та Напої': [
            {'t': 'KO', 'n': 'Coca-Cola'}, {'t': 'MCD', 'n': 'McDonald\'s'},
            {'t': 'PEP', 'n': 'PepsiCo'}, {'t': 'SBUX', 'n': 'Starbucks'}
        ],
        '💻 Техніка та IT': [
            {'t': 'AMD', 'n': 'AMD (Чіпи)'}, {'t': 'INTC', 'n': 'Intel'},
            {'t': 'SONY', 'n': 'Sony'}, {'t': 'NFLX', 'n': 'Netflix'}
        ],
        '🏦 Фінанси': [
            {'t': 'V', 'n': 'Visa'}, {'t': 'MA', 'n': 'Mastercard'},
            {'t': 'JPM', 'n': 'J.P. Morgan'}, {'t': 'PYPL', 'n': 'PayPal'}
        ],
        '🛢️ Енергія (Дивіденди)': [
             {'t': 'XOM', 'n': 'Exxon Mobil'}, {'t': 'CVX', 'n': 'Chevron'},
             {'t': 'SHEL', 'n': 'Shell'}, {'t': 'TTE', 'n': 'TotalEnergies'}
        ]
    }

    CRYPTO_CATALOG = {
        '🥇 Фундамент (Layer 1)': [
            {'t': 'BTC-USD', 'n': 'Bitcoin'}, {'t': 'ETH-USD', 'n': 'Ethereum'},
            {'t': 'SOL-USD', 'n': 'Solana'}, {'t': 'ADA-USD', 'n': 'Cardano'}
        ],
        '💸 Альткоїни та Мережі': [
            {'t': 'XRP-USD', 'n': 'XRP'}, {'t': 'DOT-USD', 'n': 'Polkadot'},
            {'t': 'AVAX-USD', 'n': 'Avalanche'}, {'t': 'LINK-USD', 'n': 'Chainlink'}
        ],
        '🐕 Мем-коїни (Високий ризик)': [
            {'t': 'DOGE-USD', 'n': 'Dogecoin'}, {'t': 'SHIB-USD', 'n': 'Shiba Inu'}
        ]
    }

    SECTOR_TRANSLATIONS = {
        'Technology': 'Технології 💻', 'Financial Services': 'Фінанси 🏦',
        'Healthcare': 'Медицина 💊', 'Consumer Cyclical': 'Авто/Споживання 🚗',
        'Consumer Defensive': 'Продукти/Напої 🍔', 'Energy': 'Енергетика ⚡',
        'Industrials': 'Промисловість 🏭', 'Communication Services': 'Телекомунікації 📡',
        'Utilities': 'Комунальні послуги 💡', 'Real Estate': 'Нерухомість 🏠',
        'Basic Materials': 'Сировина 🪨', 'Cryptocurrency': 'Криптовалюта 🪙'
    }

    def get_exchange_rate(self, from_currency, to_currency="USD"):
        """Отримує поточний курс обміну валют через Yahoo Finance."""
        if from_currency == to_currency:
            return 1.0
            
        cache_key = f"exchange_rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        if cached_rate:
            return cached_rate

        ticker_symbol = f"{from_currency}{to_currency}=X"
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 1 day history since info dict is sometimes unreliable for currencies
            hist = ticker.history(period="1d")
            if not hist.empty:
                rate = hist['Close'].iloc[-1]
                cache.set(cache_key, float(rate), 3600) # Кешуємо на 1 годину
                return float(rate)
            return 1.0
        except Exception as e:
            print(f"Помилка конвертації валюти {ticker_symbol}: {e}")
            # Fallback values if API fails
            fallbacks = {"UAHUSD": 0.025, "EURUSD": 1.08}
            return fallbacks.get(f"{from_currency}{to_currency}", 1.0)


    def search_yahoo_tickers(self, query, asset_type='EQUITY'):
        """Живий пошук (кешуємо результати пошуку на 1 день)"""
        cache_key = f"search_query_{query.lower()}_{asset_type}"
        cached_res = cache.get(cache_key)
        if cached_res: return cached_res

        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {'User-Agent': 'Mozilla/5.0'}
        params = {'q': query, 'quotesCount': 20, 'newsCount': 0, 'enableFuzzyQuery': False}
        if asset_type == 'EQUITY':
            params['quotesQueryId'] = 'tss_match_eq_basic'
        
        try:
            r = requests.get(url, params=params, headers=headers, timeout=5)
            data = r.json()
            results = []
            if 'quotes' in data:
                for item in data['quotes']:
                    if item.get('quoteType') == asset_type:
                        results.append({
                            'symbol': item['symbol'],
                            'name': item.get('shortname') or item.get('longname') or item['symbol'],
                            'exch': item.get('exchDisp', '')
                        })
            cache.set(cache_key, results, 86400) 
            return results
        except: return []

    def map_slider_to_saaty(self, value):
        mapping = {
            -4: 9.0, -3: 7.0, -2: 5.0, -1: 3.0,
            0: 1.0,
            1: 1/3.0, 2: 1/5.0, 3: 1/7.0, 4: 1/9.0
        }
        return mapping.get(round(value), 1.0)

    def calculate_weights(self, sliders):
        rp = self.map_slider_to_saaty(sliders.get("risk_profit", 0))
        rv = self.map_slider_to_saaty(sliders.get("risk_value", 0))
        rd = self.map_slider_to_saaty(sliders.get("risk_div", 0))   
        pv = self.map_slider_to_saaty(sliders.get("profit_value", 0))
        pd = self.map_slider_to_saaty(sliders.get("profit_div", 0))  
        vd = self.map_slider_to_saaty(sliders.get("value_div", 0))   

        
        matrix = np.array([
            [1,    rp,   rv,   rd],
            [1/rp, 1,    pv,   pd],
            [1/rv, 1/pv, 1,    vd],
            [1/rd, 1/pd, 1/vd, 1 ]
        ])
        
        col_sums = matrix.sum(axis=0)
        weights = (matrix / col_sums).mean(axis=1)
        
        # Обчислення Consistency Ratio (CR)
        n = 4
        ri = 0.90 # Random Index для матриці 4x4
        lambda_max = np.dot(col_sums, weights)
        ci = (lambda_max - n) / (n - 1)
        cr = ci / ri if ri > 0 else 0
        
        worst_pair_str = ""
        worst_slider_name = ""
        if cr > 0.1:
            criteria = ["Безпека", "Ріст", "Ціна", "Дохід"]
            slider_names = [
                [None, "slider_rp", "slider_rv", "slider_rd"],
                [None, None, "slider_pv", "slider_pd"],
                [None, None, None, "slider_vd"],
                [None, None, None, None]
            ]
            max_dev = 0
            for i in range(4):
                for j in range(i+1, 4):
                    eps = matrix[i, j] * (weights[j] / weights[i])
                    dev = max(eps, 1/eps) if eps > 0 else 0
                    if dev > max_dev:
                        max_dev = dev
                        worst_pair_str = f"«{criteria[i]}» та «{criteria[j]}»"
                        worst_slider_name = slider_names[i][j]
        
        return weights, cr, worst_pair_str, worst_slider_name

    def generate_sparkline(self, prices):
        """Генерує SVG шлях для міні-графіка (Пункт 1)"""
        if not prices or len(prices) < 2: return ""
        
        width, height = 120, 40
        min_p, max_p = min(prices), max(prices)
        if min_p == max_p: return f"M 0,{height/2} L {width},{height/2}"

        points = []
        for i, price in enumerate(prices):
            x = i * (width / (len(prices) - 1))
            y = height - ((price - min_p) / (max_p - min_p) * height)
            points.append(f"{x:.1f},{y:.1f}")
        
        return "M " + " L ".join(points)

    def analyze_news(self, stock_ticker_obj):
        """Аналіз настрою новин за допомогою VADER (NLP)"""
        try:
            news = stock_ticker_obj.news
            if not news: return 0, "Нейтрально 😐"
            
            analyzer = SentimentIntensityAnalyzer()
            scores = []
            
            for item in news[:7]: # Беремо 7 свіжих новин
                title = item.get('title', '')
                if not title: continue
                
                # Get VADER compound score (-1.0 to 1.0)
                vs = analyzer.polarity_scores(title)
                scores.append(vs['compound'])
            
            if not scores: return 0, "Нейтрально 😐"
            
            avg_score = sum(scores) / len(scores)
            
            # Interpret the score
            if avg_score >= 0.05:
                text = "Позитив 🟢" if avg_score < 0.5 else "Супер 🚀"
            elif avg_score <= -0.05:
                text = "Негатив 🔴" if avg_score > -0.5 else "Жах 💀"
            else:
                text = "Нейтрально 😐"
                
            return round(avg_score, 2), text
        except Exception as e:
            print(f"Sentiment Error: {e}")
            return 0, "Немає даних"

    def get_stock_data(self, tickers):
        data = []
        unique_tickers = list(set(tickers))
        REC_TRANSLATIONS = {'strong_buy': '🔥 Активно купувати', 'buy': '✅ Купувати', 'hold': '✋ Тримати', 'sell': '🔻 Продавати', 'strong_sell': '💀 Активно продавати', 'none': '❓ Немає даних'}
        
        for t in unique_tickers:
            cache_key = f"stock_v4_{t}" 
            cached_data = cache.get(cache_key)
            if cached_data:
                data.append(cached_data)
                continue

            try:
                stock = yf.Ticker(t)
                info = stock.info
                
                try:
                    hist = stock.history(period="1mo")
                    prices = hist['Close'].tolist()
                    sparkline_svg = self.generate_sparkline(prices)
                    trend_pct = ((prices[-1] - prices[0]) / prices[0]) * 100 if len(prices) > 1 else 0
                except: prices, sparkline_svg, trend_pct = [], "", 0

                sentiment_score, sentiment_text = self.analyze_news(stock)

                sector = info.get("sector", "Other")
                if info.get("quoteType") == "CRYPTOCURRENCY":
                    sector = "Cryptocurrency"
                category = self.SECTOR_TRANSLATIONS.get(sector, "Інше 📦")
                
                beta = info.get("beta"); beta = 1.5 if beta is None else beta
                pe = info.get("trailingPE"); pe = 50.0 if pe is None else pe
                profit = info.get("profitMargins"); profit = 0.0 if profit is None else profit
                div_yield = info.get("dividendYield"); div_yield = 0.0 if div_yield is None else div_yield
                rec_key = info.get('recommendationKey', 'none')

                stock_obj = {
                    "ticker": t.upper(), "name": info.get("shortName", t), "category": category,
                    "price": round(info.get("currentPrice", 0.0), 2),
                    "beta": beta, "profit": profit, "pe": pe, "div_yield": div_yield,
                    "sparkline": sparkline_svg, "trend": round(trend_pct, 1),
                    "expert_opinion": REC_TRANSLATIONS.get(rec_key, 'Невідомо'),
                    "rec_key": rec_key,
                    "sentiment_score": sentiment_score, 
                    "sentiment_text": sentiment_text    
                }
                
                cache.set(cache_key, stock_obj, 3600)
                data.append(stock_obj)
            except Exception as e:
                print(f"Error {t}: {e}")
                continue
        return data

    def get_crypto_data(self, tickers):
        data = []
        unique_tickers = list(set(tickers))
        
        for t in unique_tickers:
            cache_key = f"crypto_v1_{t}"
            cached_data = cache.get(cache_key)
            if cached_data:
                data.append(cached_data)
                continue

            try:
                stock = yf.Ticker(t)
                info = stock.info
                
                try:
                    hist = stock.history(period="1mo")
                    prices = hist['Close'].tolist()
                    sparkline_svg = self.generate_sparkline(prices)
                except: prices, sparkline_svg = [], ""
                
                sentiment_score, sentiment_text = self.analyze_news(stock)
                
                market_cap = info.get("marketCap", 1)
                volume = info.get("volume24Hr", info.get("regularMarketVolume", 1))
                trend_50d = info.get("fiftyDayAverageChangePercent", 0.0) * 100
                discount = info.get("fiftyTwoWeekHighChangePercent", 0.0) * 100
                
                raw_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                
                crypto_obj = {
                    "ticker": t.upper(), "name": info.get("shortName", t), "category": "Криптовалюта 🪙",
                    "price": raw_price,
                    "price_display": f"{raw_price:.8f}".rstrip('0').rstrip('.') if raw_price < 0.01 else f"{raw_price:.2f}",
                    "market_cap": market_cap, "volume": volume, "trend_50d": trend_50d, "discount": discount,
                    "sparkline": sparkline_svg, "trend": round(trend_50d, 1),
                    "sentiment_score": sentiment_score, 
                    "sentiment_text": sentiment_text    
                }
                
                cache.set(cache_key, crypto_obj, 3600)
                data.append(crypto_obj)
            except Exception as e:
                print(f"Error Crypto {t}: {e}")
                continue
        return data

    def rank_stocks(self, stock_data, weights):
        
        if not stock_data: return []
        betas = np.array([d["beta"] for d in stock_data])
        profits = np.array([d["profit"] for d in stock_data])
        pes = np.array([d["pe"] for d in stock_data])
        divs = np.array([d["div_yield"] for d in stock_data])

        inv_betas = 1 / (betas + 0.01)
        norm_risk = inv_betas / inv_betas.sum()
        clean_profits = np.maximum(profits, 0)
        norm_profit = clean_profits / (clean_profits.sum() + 0.0001)
        inv_pes = 1 / (pes + 0.01)
        norm_pe = inv_pes / inv_pes.sum()
        norm_div = divs / (divs.sum() + 0.0001)

        metrics_matrix = np.column_stack((norm_risk, norm_profit, norm_pe, norm_div))
        scores = np.dot(metrics_matrix, weights)
        
        results = []
        for i, item in enumerate(stock_data):
            score = round(scores[i] * 100, 1)
            contributions = {
                "Надійність 🛡️": norm_risk[i] * weights[0],
                "Ріст 🚀": norm_profit[i] * weights[1],
                "Дешевизна 🏷️": norm_pe[i] * weights[2],
                "Дивіденди 💰": norm_div[i] * weights[3]
            }
            item["score"] = score
            item["metrics_display"] = {
                "beta": round(betas[i], 2),
                "profit": round(profits[i] * 100, 1),
                "pe": round(pes[i], 1),
                "div": round(divs[i] * 100, 2)
            }
            item["reason"] = max(contributions, key=contributions.get)
            results.append(item)
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def rank_crypto(self, crypto_data, weights):
        if not crypto_data: return []
        
        m_caps = np.array([d["market_cap"] for d in crypto_data])
        vols = np.array([d["volume"] for d in crypto_data])
        trends = np.array([d["trend_50d"] for d in crypto_data])
        discounts = np.array([d["discount"] for d in crypto_data])
        
        norm_mcap = m_caps / (m_caps.sum() + 0.0001)
        norm_vol = vols / (vols.sum() + 0.0001)
        
        clean_trends = np.maximum(trends, 0)
        if clean_trends.sum() == 0: 
            norm_trend = np.ones(len(trends)) / len(trends)
        else: 
            norm_trend = clean_trends / (clean_trends.sum() + 0.0001)
        
        inv_discount = np.abs(discounts)
        norm_discount = inv_discount / (inv_discount.sum() + 0.0001)

        metrics_matrix = np.column_stack((norm_mcap, norm_vol, norm_trend, norm_discount))
        scores = np.dot(metrics_matrix, weights)
        
        results = []
        for i, item in enumerate(crypto_data):
            score = round(scores[i] * 100, 1)
            contributions = {
                "Надійність 🛡️": norm_mcap[i] * weights[0],
                "Активність 📊": norm_vol[i] * weights[1],
                "Тенденція 🚀": norm_trend[i] * weights[2],
                "Знижка 🏷️": norm_discount[i] * weights[3]
            }
            item["score"] = score
            item["metrics_display"] = {
                "mcap": f"${item['market_cap'] / 1e9:.1f}B" if item['market_cap'] > 1e9 else f"${item['market_cap'] / 1e6:.1f}M",
                "vol": f"${item['volume'] / 1e9:.1f}B" if item['volume'] > 1e9 else f"${item['volume'] / 1e6:.1f}M",
                "trend": round(trends[i], 1),
                "discount": round(discounts[i], 1)
            }
            item["metrics_raw"] = {
                "mcap": round(norm_mcap[i] * 100, 1),
                "vol": round(norm_vol[i] * 100, 1),
                "trend": round(norm_trend[i] * 100, 1),
                "discount": round(norm_discount[i] * 100, 1)
            }
            item["reason"] = max(contributions, key=contributions.get)
            results.append(item)
        return sorted(results, key=lambda x: x["score"], reverse=True)