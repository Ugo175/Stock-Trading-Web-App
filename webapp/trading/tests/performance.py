from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from trading.models import Portfolio, PortfolioSnapshot, PerformanceMetric
from django.contrib.auth.models import User

class PerformanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='12345')
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            balance=Decimal('1000.00')
        )

    def test_portfolio_snapshot(self):
        snapshot = self.portfolio.create_daily_snapshot()
        self.assertEqual(snapshot.total_value, self.portfolio.balance)
        self.assertEqual(snapshot.cash_balance, self.portfolio.balance)

    def test_performance_metric_creation(self):
        metric = PerformanceMetric.objects.create(
            portfolio=self.portfolio,
            date=timezone.now().date(),
            daily_return=Decimal('1.5'),
            total_return=Decimal('5.0'),
            realized_gain_loss=Decimal('100.00'),
            unrealized_gain_loss=Decimal('50.00')
        )
        self.assertEqual(metric.daily_return, Decimal('1.5'))
        self.assertEqual(metric.total_return, Decimal('5.0'))