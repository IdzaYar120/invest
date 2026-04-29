from django.shortcuts import render
from django.http import JsonResponse
from .utils import InvestmentAHP
import json 

def analyze(request):
    engine = InvestmentAHP()
    
    if request.method == "POST":
        tickers_input = request.POST.get('tickers_hidden', '')
        tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers:
             return render(request, "analyzer/dashboard.html", {
                "catalog": engine.STOCK_CATALOG,
                "error_message": "Спочатку додайте хоча б одну компанію! 📉"
            })

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

        try:
            budget_amount = float(request.POST.get("budget_amount") or 0)
            budget_currency = request.POST.get("budget_currency", "USD")
        except ValueError:
            budget_amount = 0.0
            budget_currency = "USD"

        weights, cr, worst_pair, worst_slider = engine.calculate_weights(sliders)
        raw_data = engine.get_stock_data(tickers)
        results = engine.rank_stocks(raw_data, weights)
        
        exchange_rate = engine.get_exchange_rate(budget_currency, "USD")
        total_budget_usd = budget_amount * exchange_rate
        
        if total_budget_usd > 0:
            for item in results:
                allocated_usd = total_budget_usd * (item['score'] / 100.0)
                item['allocated_usd'] = round(allocated_usd, 2)
                if item['price'] > 0:
                    item['shares_to_buy'] = round(allocated_usd / item['price'], 4)
                else:
                    item['shares_to_buy'] = 0.0

        
        restored_names = {item['ticker']: item['name'] for item in results}
        
        context = {
            "results": results, 
            "sliders": sliders,
            "budget_amount": budget_amount,
            "budget_currency": budget_currency,
            "total_budget_usd": round(total_budget_usd, 2) if total_budget_usd > 0 else 0,
            "selected_tickers": ",".join(tickers),
            "restored_names_json": json.dumps(restored_names), 
            "catalog": engine.STOCK_CATALOG,
            "weights": {
                "Risk": round(weights[0]*100), 
                "Profit": round(weights[1]*100), 
                "Value": round(weights[2]*100),
                "Div": round(weights[3]*100)
            },
            "cr": round(cr, 2),
            "is_consistent": cr <= 0.1,
            "worst_pair": worst_pair,
            "worst_slider": worst_slider
        }
        return render(request, "analyzer/dashboard.html", context)
    
    return render(request, "analyzer/dashboard.html", {"catalog": engine.STOCK_CATALOG})

def ticker_search(request):
    query = request.GET.get('q', '')
    if len(query) < 1: return JsonResponse({'results': []})
    engine = InvestmentAHP()
    results = engine.search_yahoo_tickers(query)
    return JsonResponse({'results': results})