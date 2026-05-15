from django.db import models
import uuid

class PriceAlert(models.Model):
    CONDITION_CHOICES = [
        ('above', 'Ціна підніметься вище'),
        ('below', 'Ціна впаде нижче'),
    ]

    email = models.EmailField(verbose_name='Email')
    ticker = models.CharField(max_length=10, verbose_name='Тікер')
    target_price = models.FloatField(verbose_name='Цільова ціна')
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, verbose_name='Умова')
    is_active = models.BooleanField(default=True, verbose_name='Активне')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.ticker} {self.condition} {self.target_price}"

    class Meta:
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'

def generate_short_id():
    return uuid.uuid4().hex[:8]

class SharedPortfolio(models.Model):
    id = models.CharField(max_length=10, primary_key=True, default=generate_short_id)
    portfolio_type = models.CharField(max_length=20)
    tickers = models.TextField()
    sliders = models.JSONField(default=dict)
    budget_amount = models.FloatField(default=0)
    budget_currency = models.CharField(max_length=10, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shared {self.portfolio_type} ({self.id})"
