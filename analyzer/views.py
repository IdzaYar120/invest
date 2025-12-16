from django.shortcuts import render
from django.http import JsonResponse
from .utils import InvestmentAHP
import json # <-- Додайте цей імпорт, якщо його немає

def analyze(request):
    engine = InvestmentAHP()
    
    if request.method == "POST":
        tickers_input = request.POST.get('tickers_hidden', '')
        # Чистимо від зайвих пробілів
        tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers: tickers = ["AAPL", "MSFT", "KO"]

        try:
            sliders = {
                "risk_profit": float(request.POST.get("slider_rp", 0)),
                "risk_value": float(request.POST.get("slider_rv", 0)),
                "profit_value": float(request.POST.get("slider_pv", 0)),
                "profit_div": float(request.POST.get("slider_pd", 0)),
                "risk_div": float(request.POST.get("slider_rd", 0)),
                "value_div": float(request.POST.get("slider_vd", 0)),
            }
        except ValueError: 
            sliders = {k:0 for k in ["risk_profit", "risk_value", "profit_value", "profit_div", "risk_div", "value_div"]}

        weights = engine.calculate_weights(sliders)
        raw_data = engine.get_stock_data(tickers)
        results = engine.rank_stocks(raw_data, weights)
        
        # Створюємо словник імен для відновлення красивих назв
        # { 'AAPL': 'Apple', 'MSFT': 'Microsoft' ... }
        restored_names = {item['ticker']: item['name'] for item in results}
        
        context = {
            "results": results, 
            "sliders": sliders,
            # Повертаємо чистий рядок тікерів
            "selected_tickers": ",".join(tickers),
            # Передаємо імена як JSON для JavaScript
            "restored_names_json": json.dumps(restored_names), 
            "catalog": engine.STOCK_CATALOG,
            "weights": {
                "Risk": round(weights[0]*100), 
                "Profit": round(weights[1]*100), 
                "Value": round(weights[2]*100),
                "Div": round(weights[3]*100)
            }
        }
        return render(request, "analyzer/dashboard.html", context)
    
    return render(request, "analyzer/dashboard.html", {"catalog": engine.STOCK_CATALOG})

def ticker_search(request):
    query = request.GET.get('q', '')
    if len(query) < 1: return JsonResponse({'results': []})
    engine = InvestmentAHP()
    results = engine.search_yahoo_tickers(query)
    return JsonResponse({'results': results})