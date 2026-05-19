from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from .utils import InvestmentAHP
from .models import PriceAlert
from django.utils import timezone
import json 
import io
import concurrent.futures
import yfinance as yf

try:
    from xhtml2pdf import pisa  # type: ignore
except ImportError:
    pisa = None

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
                "risk_profit": float(request.POST.get("slider_rp") or 0),
                "risk_value": float(request.POST.get("slider_rv") or 0),
                "profit_value": float(request.POST.get("slider_pv") or 0),
                "profit_div": float(request.POST.get("slider_pd") or 0),
                "risk_div": float(request.POST.get("slider_rd") or 0),
                "value_div": float(request.POST.get("slider_vd") or 0),
            }
        except (ValueError, TypeError): 
            sliders = {k:0 for k in ["risk_profit", "risk_value", "profit_value", "profit_div", "risk_div", "value_div"]}

        try:
            budget_amount = float(request.POST.get("budget_amount") or 0)
            budget_currency = request.POST.get("budget_currency") or "USD"
        except (ValueError, TypeError):
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
            "generation_time": timezone.localtime().strftime("%d.%m.%Y, %H:%M"),
            "cr": round(cr, 2),
            "is_consistent": cr <= 0.1,
            "worst_pair": worst_pair,
            "worst_slider": worst_slider
        }

        # Глибокий аналіз ризиків (Кореляція та Марковіц)
        risk_analysis = engine.get_portfolio_analysis(tickers)
        if risk_analysis:
            # Zip labels and values for easier iteration in template
            risk_analysis["correlation"]["zipped"] = zip(
                risk_analysis["correlation"]["labels"], 
                risk_analysis["correlation"]["values"]
            )
            context["risk_analysis"] = risk_analysis

        # Аналіз концентрації в секторах
        sector_counts = {}
        for item in results:
            s = item.get('raw_sector', 'Other')
            sector_counts[s] = sector_counts.get(s, 0) + (item['score'] / 100)
        
        total_score_sum = sum(item['score'] for item in results) / 100
        sector_stats = []
        sector_warnings = []
        for s, score_sum in sector_counts.items():
            pct = (score_sum / total_score_sum) * 100 if total_score_sum > 0 else 0
            sector_stats.append({"name": engine.SECTOR_TRANSLATIONS.get(s, s), "pct": round(pct, 1)})
            if pct > 40 and len(results) > 2:
                sector_warnings.append(f"Зависока концентрація у секторі <b>{engine.SECTOR_TRANSLATIONS.get(s, s)}</b> ({round(pct,1)}%). Розгляньте диверсифікацію.")
        
        context["sector_stats"] = sector_stats
        context["sector_warnings"] = sector_warnings

        if total_budget_usd > 0:
            context["backtest"] = engine.get_backtest_data(results, total_budget_usd)

        return render(request, "analyzer/dashboard.html", context)
    
    return render(request, "analyzer/dashboard.html", {"catalog": engine.STOCK_CATALOG})

def ticker_search(request):
    query = request.GET.get('q', '')
    asset_type = request.GET.get('type', 'equity').upper()
    if len(query) < 1: return JsonResponse({'results': []})
    engine = InvestmentAHP()
    results = engine.search_yahoo_tickers(query, asset_type)
    return JsonResponse({'results': results})

def export_pdf(request):
    if not pisa:
        return HttpResponse("xhtml2pdf is not installed", status=500)
        
    engine = InvestmentAHP()
    if request.method == "POST":
        tickers_input = request.POST.get('tickers_hidden', '')
        tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers:
            return HttpResponse("Немає даних для експорту", status=400)
            
        try:
            sliders = {
                "risk_profit": float(request.POST.get("slider_rp") or 0),
                "risk_value": float(request.POST.get("slider_rv") or 0),
                "profit_value": float(request.POST.get("slider_pv") or 0),
                "profit_div": float(request.POST.get("slider_pd") or 0),
                "risk_div": float(request.POST.get("slider_rd") or 0),
                "value_div": float(request.POST.get("slider_vd") or 0),
            }
        except (ValueError, TypeError): 
            sliders = {k:0 for k in ["risk_profit", "risk_value", "profit_value", "profit_div", "risk_div", "value_div"]}

        try:
            budget_amount = float(request.POST.get("budget_amount") or 0)
            budget_currency = request.POST.get("budget_currency") or "USD"
        except (ValueError, TypeError):
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

        context = {
            "results": results, 
            "budget_amount": budget_amount,
            "budget_currency": budget_currency,
            "total_budget_usd": round(total_budget_usd, 2) if total_budget_usd > 0 else 0,
            "weights": {
                "Risk": round(weights[0]*100), 
                "Profit": round(weights[1]*100), 
                "Value": round(weights[2]*100),
                "Div": round(weights[3]*100)
            }
        }
        
        html_string = render_to_string('analyzer/pdf_template.html', context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="invest_portfolio_report.pdf"'
        
        pisa_status = pisa.CreatePDF(
            html_string, dest=response, encoding='utf-8')
            
        if pisa_status.err:
            return HttpResponse('Помилка генерації PDF <pre>' + html_string + '</pre>')
        return response
    
    return HttpResponse("Invalid request method", status=400)

def export_csv(request):
    return HttpResponse("CSV export is handled on frontend. See JS exportCSV().", status=200)

def crypto_analyze(request):
    engine = InvestmentAHP()
    
    if request.method == "POST":
        tickers_input = request.POST.get('tickers_hidden', '')
        tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers:
             return render(request, "analyzer/crypto_dashboard.html", {
                "catalog": engine.CRYPTO_CATALOG,
                "error_message": "Спочатку додайте хоча б одну криптовалюту! 📉"
            })

        try:
            sliders = {
                "risk_profit": float(request.POST.get("slider_rp") or 0),
                "risk_value": float(request.POST.get("slider_rv") or 0),
                "profit_value": float(request.POST.get("slider_pv") or 0),
                "profit_div": float(request.POST.get("slider_pd") or 0),
                "risk_div": float(request.POST.get("slider_rd") or 0),
                "value_div": float(request.POST.get("slider_vd") or 0),
            }
        except (ValueError, TypeError): 
            sliders = {k:0 for k in ["risk_profit", "risk_value", "profit_value", "profit_div", "risk_div", "value_div"]}

        try:
            budget_amount = float(request.POST.get("budget_amount") or 0)
            budget_currency = request.POST.get("budget_currency") or "USD"
        except (ValueError, TypeError):
            budget_amount = 0.0
            budget_currency = "USD"

        weights, cr, worst_pair, worst_slider = engine.calculate_weights(sliders)
        raw_data = engine.get_crypto_data(tickers)
        results = engine.rank_crypto(raw_data, weights)
        
        exchange_rate = engine.get_exchange_rate(budget_currency, "USD")
        total_budget_usd = budget_amount * exchange_rate
        
        if total_budget_usd > 0:
            for item in results:
                allocated_usd = total_budget_usd * (item['score'] / 100.0)
                item['allocated_usd'] = round(allocated_usd, 2)
                if item['price'] > 0:
                    shares = allocated_usd / item['price']
                    if shares < 1:
                        item['shares_to_buy'] = round(shares, 4)
                    elif shares < 1000:
                        item['shares_to_buy'] = round(shares, 2)
                    else:
                        item['shares_to_buy'] = f"{int(shares):,}".replace(",", " ")
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
            "catalog": engine.CRYPTO_CATALOG,
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
        if total_budget_usd > 0:
            context["backtest"] = engine.get_backtest_data(results, total_budget_usd)
            
        return render(request, "analyzer/crypto_dashboard.html", context)
    
    return render(request, "analyzer/crypto_dashboard.html", {"catalog": engine.CRYPTO_CATALOG})
def create_alert(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            PriceAlert.objects.create(
                email=data['email'],
                ticker=data['ticker'].upper(),
                target_price=float(data['target_price']),
                condition=data['condition']
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def api_crypto_prices(request):
    tickers = request.GET.get('tickers', '')
    if not tickers:
        return JsonResponse({})
    tickers_list = [t.strip() for t in tickers.split(',') if t.strip()]
    prices = {}
    
    def fetch_price(t):
        try:
            info = yf.Ticker(t).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            return t, price
        except:
            return t, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for t, price in executor.map(fetch_price, tickers_list):
            if price is not None and price > 0:
                prices[t] = {
                    "price": price,
                    "price_display": f"{price:.8f}".rstrip('0').rstrip('.') if price < 0.01 else f"{price:.2f}"
                }
    return JsonResponse(prices)

from django.urls import reverse
from .models import SharedPortfolio

def create_shared_portfolio(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            portfolio_type = data.get('portfolio_type', 'crypto')
            tickers = data.get('tickers', '')
            sliders = data.get('sliders', {})
            budget_amount = float(data.get('budget_amount', 0) or 0)
            budget_currency = data.get('budget_currency', 'USD')

            if not tickers:
                return JsonResponse({'status': 'error', 'message': 'No tickers provided'})

            shared = SharedPortfolio.objects.create(
                portfolio_type=portfolio_type,
                tickers=tickers,
                sliders=sliders,
                budget_amount=budget_amount,
                budget_currency=budget_currency
            )
            
            share_url = request.build_absolute_uri(reverse('view_shared_portfolio', args=[shared.id]))
            return JsonResponse({'status': 'success', 'url': share_url})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def view_shared_portfolio(request, share_id):
    try:
        shared = SharedPortfolio.objects.get(id=share_id)
    except SharedPortfolio.DoesNotExist:
        return HttpResponse("Portfolio not found", status=404)
        
    engine = InvestmentAHP()
    tickers = [t.strip() for t in shared.tickers.split(',') if t.strip()]
    sliders = shared.sliders
    budget_amount = shared.budget_amount
    budget_currency = shared.budget_currency
    
    weights, cr, worst_pair, worst_slider = engine.calculate_weights(sliders)
    exchange_rate = engine.get_exchange_rate(budget_currency, "USD")
    total_budget_usd = budget_amount * exchange_rate
    
    if shared.portfolio_type == 'crypto':
        raw_data = engine.get_crypto_data(tickers)
        results = engine.rank_crypto(raw_data, weights)
        template_name = "analyzer/crypto_dashboard.html"
        catalog = engine.CRYPTO_CATALOG
    else:
        raw_data = engine.get_stock_data(tickers)
        results = engine.rank_stocks(raw_data, weights)
        template_name = "analyzer/dashboard.html"
        catalog = engine.STOCK_CATALOG
        
    if total_budget_usd > 0:
        for item in results:
            allocated_usd = total_budget_usd * (item['score'] / 100.0)
            item['allocated_usd'] = round(allocated_usd, 2)
            if item['price'] > 0:
                shares = allocated_usd / item['price']
                if shares < 1: item['shares_to_buy'] = round(shares, 4)
                elif shares < 1000: item['shares_to_buy'] = round(shares, 2)
                else: item['shares_to_buy'] = f"{int(shares):,}".replace(",", " ")
            else:
                item['shares_to_buy'] = 0.0

    restored_names = {item['ticker']: item['name'] for item in results}
    
    context = {
        "results": results, 
        "sliders": sliders,
        "budget_amount": budget_amount,
        "budget_currency": budget_currency,
        "total_budget_usd": round(total_budget_usd, 2) if total_budget_usd > 0 else 0,
        "selected_tickers": shared.tickers,
        "restored_names_json": json.dumps(restored_names), 
        "catalog": catalog,
        "weights": {
            "Risk": round(weights[0]*100), 
            "Profit": round(weights[1]*100), 
            "Value": round(weights[2]*100),
            "Div": round(weights[3]*100)
        },
        "cr": round(cr, 2),
        "is_consistent": cr <= 0.1,
        "worst_pair": worst_pair,
        "worst_slider": worst_slider,
        "is_shared": True
    }
    
    if shared.portfolio_type == 'crypto' and total_budget_usd > 0:
        context["backtest"] = engine.get_backtest_data(results, total_budget_usd)
        
    if shared.portfolio_type == 'stock':
        risk_analysis = engine.get_portfolio_analysis(tickers)
        if risk_analysis:
            risk_analysis["correlation"]["zipped"] = zip(
                risk_analysis["correlation"]["labels"], 
                risk_analysis["correlation"]["values"]
            )
            context["risk_analysis"] = risk_analysis
            
        sector_counts = {}
        for item in results:
            s = item.get('raw_sector', 'Other')
            sector_counts[s] = sector_counts.get(s, 0) + (item['score'] / 100)
        
        total_score_sum = sum(item['score'] for item in results) / 100
        sector_stats = []
        sector_warnings = []
        for s, score_sum in sector_counts.items():
            pct = (score_sum / total_score_sum) * 100 if total_score_sum > 0 else 0
            sector_stats.append({"name": engine.SECTOR_TRANSLATIONS.get(s, s), "pct": round(pct, 1)})
            if pct > 40 and len(results) > 2:
                sector_warnings.append(f"Зависока концентрація у секторі <b>{engine.SECTOR_TRANSLATIONS.get(s, s)}</b> ({round(pct,1)}%). Розгляньте диверсифікацію.")
        
        context["sector_stats"] = sector_stats
        context["sector_warnings"] = sector_warnings
        if total_budget_usd > 0:
            context["backtest"] = engine.get_backtest_data(results, total_budget_usd)

    return render(request, template_name, context)
