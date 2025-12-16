import numpy as np
import yfinance as yf
import requests
from django.core.cache import cache 

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

    SECTOR_TRANSLATIONS = {
        'Technology': 'Технології 💻', 'Financial Services': 'Фінанси 🏦',
        'Healthcare': 'Медицина 💊', 'Consumer Cyclical': 'Авто/Споживання 🚗',
        'Consumer Defensive': 'Продукти/Напої 🍔', 'Energy': 'Енергетика ⚡',
        'Industrials': 'Промисловість 🏭', 'Communication Services': 'Телекомунікації 📡',
        'Utilities': 'Комунальні послуги 💡', 'Real Estate': 'Нерухомість 🏠',
        'Basic Materials': 'Сировина 🪨'
    }

    def search_yahoo_tickers(self, query):
        """Живий пошук (кешуємо результати пошуку на 1 день)"""
        cache_key = f"search_query_{query.lower()}"
        cached_res = cache.get(cache_key)
        if cached_res: return cached_res

        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {'User-Agent': 'Mozilla/5.0'}
        params = {'q': query, 'quotesCount': 5, 'newsCount': 0, 'enableFuzzyQuery': False, 'quotesQueryId': 'tss_match_eq_basic'}
        
        try:
            r = requests.get(url, params=params, headers=headers, timeout=5)
            data = r.json()
            results = []
            if 'quotes' in data:
                for item in data['quotes']:
                    if item.get('quoteType') == 'EQUITY':
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
        return (matrix / col_sums).mean(axis=1)

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
        """Простий аналіз заголовків новин на позитив/негатив"""
        try:
            news = stock_ticker_obj.news
            if not news: return 0, "Нейтрально 😐"
            
            score = 0
            positive_words = ['up', 'growth', 'profit', 'record', 'gain', 'bull', 'high', 'success', 'buy', 'strong']
            negative_words = ['down', 'loss', 'drop', 'crash', 'bear', 'low', 'fail', 'sell', 'weak', 'lawsuit']

            for item in news[:5]: 
                title = item.get('title', '').lower()
                for w in positive_words: 
                    if w in title: score += 1
                for w in negative_words: 
                    if w in title: score -= 1
            
            if score >= 2: return score, "Позитив 🟢"
            if score <= -2: return score, "Негатив 🔴"
            return score, "Нейтрально 😐"
        except:
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