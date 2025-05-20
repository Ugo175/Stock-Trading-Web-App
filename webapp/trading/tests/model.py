from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from trading.models import Stock, Portfolio, StockHolding, Transaction

class StockModelTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=Decimal('150.00')
        )

    def test_stock_creation(self):
        self.assertEqual(self.stock.symbol, "AAPL")
        self.assertEqual(self.stock.current_price, Decimal('150.00'))

    def test_symbol_uppercase(self):
        stock = Stock.objects.create(
            symbol="googl",
            name="Google",
            current_price=Decimal('100.00')
        )
        self.assertEqual(stock.symbol, "GOOGL")

    def test_negative_price_validation(self):
        with self.assertRaises(ValidationError):
            Stock.objects.create(
                symbol="MSFT",
                name="Microsoft",
                current_price=Decimal('-50.00')
            )

class PortfolioModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            balance=Decimal('1000.00')
        )
        self.stock = Stock.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=Decimal('150.00')
        )

    def test_portfolio_creation(self):
        self.assertEqual(self.portfolio.balance, Decimal('1000.00'))
        self.assertEqual(self.portfolio.user.username, 'testuser')

    def test_can_buy_stock(self):
        # Test with sufficient funds
        self.assertTrue(self.portfolio.can_buy_stock(self.stock, 5))
        
        # Test with insufficient funds
        self.assertFalse(self.portfolio.can_buy_stock(self.stock, 10))

    def test_buy_stock(self):
        # Test buying stock
        self.portfolio.buy_stock(self.stock, 2)
        
        # Check balance was deducted
        expected_balance = Decimal('1000.00') - (Decimal('150.00') * 2)
        self.assertEqual(self.portfolio.balance, expected_balance)
        
        # Check holding was created
        holding = StockHolding.objects.get(portfolio=self.portfolio, stock=self.stock)
        self.assertEqual(holding.quantity, 2)
        
        # Check transaction was recorded
        transaction = Transaction.objects.get(user=self.user, stock=self.stock)
        self.assertEqual(transaction.transaction_type, 'BUY')
        self.assertEqual(transaction.quantity, 2)

    def test_insufficient_funds(self):
        with self.assertRaises(ValidationError):
            self.portfolio.buy_stock(self.stock, 10)