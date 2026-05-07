from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from analyzer.models import PriceAlert
import yfinance as yf

class Command(BaseCommand):
    help = 'Перевіряє поточні ціни на активи і надсилає листи (в консоль)'

    def handle(self, *args, **options):
        alerts = PriceAlert.objects.filter(is_active=True)
        if not alerts.exists():
            self.stdout.write(self.style.SUCCESS('Немає активних сповіщень для перевірки.'))
            return

        for alert in alerts:
            try:
                ticker_obj = yf.Ticker(alert.ticker)
                info = ticker_obj.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                
                if current_price is None:
                    continue

                triggered = False
                if alert.condition == 'above' and current_price >= alert.target_price:
                    triggered = True
                elif alert.condition == 'below' and current_price <= alert.target_price:
                    triggered = True

                if triggered:
                    subject = f"🔔 Invest Pro: Ціна {alert.ticker} досягла вашої цілі!"
                    message = f"""
Вітаємо!

Ви встановлювали сповіщення на актив {alert.ticker}.
Умова: ціна має бути {'більшою' if alert.condition == 'above' else 'меншою'} за ${alert.target_price}.
Поточна ціна: ${current_price}.

Час діяти!
З повагою, Invest Pro 2.0
"""
                    send_mail(
                        subject,
                        message,
                        'noreply@investpro.com',
                        [alert.email],
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Сповіщення надіслано на {alert.email} для {alert.ticker}"))
                    
                    # Деактивуємо після спрацювання
                    alert.is_active = False
                    alert.save()

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Помилка перевірки {alert.ticker}: {e}"))
