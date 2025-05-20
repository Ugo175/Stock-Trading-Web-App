from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

class Stock(models.Model):
    """
    Represents a stock in the market with its current price information.
    
    This model stores essential information about stocks including their symbol,
    company name, and current price. The last_updated field tracks when the price
    was last updated from an external data source.
    """
    symbol = models.CharField(max_length=10, unique=True, db_index=True)  # Stock ticker symbol (e.g., AAPL for Apple)
    name = models.CharField(max_length=100)  # Full company name
    current_price = models.DecimalField(max_digits=10, decimal_places=2)  # Current stock price
    last_updated = models.DateTimeField(default=timezone.now)  # Timestamp of last price update

    class Meta:
        # Adding indexes to improve query performance for common search fields
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['name'])
        ]

    def clean(self):
        """
        Validates the stock data before saving:
        - Converts the symbol to uppercase for consistency
        - Ensures the stock price is positive
        """
        self.symbol = self.symbol.upper()
        if self.current_price <= 0:
            raise ValidationError("Stock price must be positive")

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure data validation before saving to the database
        """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns a human-readable string representation of the stock"""
        return f"{self.symbol} - {self.name}"

class Portfolio(models.Model):
    """
    Represents a user's investment portfolio.
    
    Each user has one portfolio that tracks their cash balance and is linked to their
    stock holdings. The portfolio provides methods for buying stocks and calculating
    its total value.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to Django's built-in User model
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Cash balance available for trading
    created_at = models.DateTimeField(auto_now_add=True)  # When the portfolio was created

    def can_buy_stock(self, stock, quantity):
        """
        Determines if the user has sufficient funds to purchase the specified quantity of a stock
        
        Args:
            stock: The Stock object to purchase
            quantity: Number of shares to buy
            
        Returns:
            bool: True if user has enough funds, False otherwise
        """
        total_cost = stock.current_price * Decimal(quantity)
        return self.balance >= total_cost

    def buy_stock(self, stock, quantity):
        """
        Executes a stock purchase if the user has sufficient funds.
        
        This method:
        1. Verifies sufficient funds
        2. Deducts the cost from the user's balance
        3. Updates or creates the appropriate StockHolding
        4. Creates a transaction record
        
        Args:
            stock: The Stock object to purchase
            quantity: Number of shares to buy
            
        Raises:
            ValidationError: If the user has insufficient funds
        """
        if not self.can_buy_stock(stock, quantity):
            raise ValidationError("Insufficient funds")
        
        total_cost = stock.current_price * Decimal(quantity)
        self.balance -= total_cost
        self.save()

        # Get or create a holding for this stock
        holding, created = StockHolding.objects.get_or_create(
            portfolio=self,
            stock=stock,
            defaults={'quantity': 0}
        )
        holding.quantity += quantity
        holding.save()

        # Record the transaction
        Transaction.objects.create(
            user=self.user,
            stock=stock,
            transaction_type='BUY',
            quantity=quantity,
            price=stock.current_price
        )

    def calculate_total_value(self):
        """
        Calculates the total value of the portfolio including:
        - Cash balance
        - Current market value of all stock holdings
        
        Returns:
            Decimal: The total portfolio value
        """
        holdings_value = sum(
            holding.stock.current_price * holding.quantity 
            for holding in self.holdings.all()
        )
        return self.balance + holdings_value

    def create_daily_snapshot(self):
        """
        Creates a daily snapshot of the portfolio's value for historical tracking.
        
        Returns:
            PortfolioSnapshot: The created snapshot object
        """
        return PortfolioSnapshot.objects.create(
            portfolio=self,
            total_value=self.calculate_total_value(),
            cash_balance=self.balance
        )

    def __str__(self):
        """Returns a human-readable string representation of the portfolio"""
        return f"{self.user.username}'s Portfolio (${self.balance})"

class StockHolding(models.Model):
    """
    Represents shares of a specific stock held in a user's portfolio.
    
    This model links a portfolio to a stock and records how many shares are owned.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')  # Link to the owner's portfolio
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)  # Link to the stock being held
    quantity = models.PositiveIntegerField(default=0)  # Number of shares owned
    
    class Meta:
        # Ensure a user can only have one holding entry per stock
        unique_together = ['portfolio', 'stock']
        # Index for performance optimization for common queries
        indexes = [
            models.Index(fields=['portfolio', 'stock'])
        ]

    def clean(self):
        """
        Validates that the holding quantity is not negative
        """
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative")

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure validation before saving
        """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns a human-readable string representation of the holding"""
        return f"{self.portfolio.user.username} - {self.stock.symbol}: {self.quantity}"

class Transaction(models.Model):
    """
    Records all buy and sell transactions made by users.
    
    Each transaction captures details about what stock was traded, at what price,
    in what quantity, and by whom. Used for historical tracking and reporting.
    """
    TRANSACTION_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # User who made the transaction
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)  # Stock that was traded
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)  # Whether it was a buy or sell
    quantity = models.PositiveIntegerField()  # Number of shares traded
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per share at time of transaction
    timestamp = models.DateTimeField(auto_now_add=True)  # When the transaction occurred
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Total cost/proceeds of transaction

    class Meta:
        # Indexes for common queries to improve performance
        indexes = [
            models.Index(fields=['user', 'timestamp']),  # For user transaction history
            models.Index(fields=['stock', 'timestamp'])  # For stock transaction history
        ]

    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically calculate the total amount
        for the transaction before saving
        """
        self.total_amount = self.price * Decimal(self.quantity)
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns a human-readable string representation of the transaction"""
        return f"{self.transaction_type} {self.quantity} {self.stock.symbol} @ ${self.price}"

class PortfolioSnapshot(models.Model):
    """
    Records the value of a portfolio at a specific point in time.
    
    These snapshots are used for historical tracking and performance analysis,
    capturing both the total value and cash component separately.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='snapshots')  # The portfolio being tracked
    total_value = models.DecimalField(max_digits=12, decimal_places=2)  # Total portfolio value (cash + holdings)
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2)  # Cash component of the portfolio
    timestamp = models.DateTimeField(default=timezone.now)  # When the snapshot was taken
    
    class Meta:
        # Index for timeline queries
        indexes = [
            models.Index(fields=['portfolio', 'timestamp']),
        ]
        
    def __str__(self):
        """Returns a human-readable string representation of the snapshot"""
        return f"{self.portfolio.user.username}'s Portfolio Value: ${self.total_value} at {self.timestamp}"
    
class PerformanceMetric(models.Model):
    """
    Tracks various performance metrics for a portfolio on a daily basis.
    
    This model is used for analyzing investment performance over time,
    capturing metrics like daily returns and gain/loss values.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='metrics')  # The portfolio being measured
    date = models.DateField()  # Date of the metrics
    daily_return = models.DecimalField(max_digits=8, decimal_places=4)  # Day-over-day return percentage
    total_return = models.DecimalField(max_digits=8, decimal_places=4)  # Total return percentage since inception
    realized_gain_loss = models.DecimalField(max_digits=12, decimal_places=2)  # Gain/loss from closed positions
    unrealized_gain_loss = models.DecimalField(max_digits=12, decimal_places=2)  # Gain/loss from current holdings
    
    class Meta:
        # Ensure one set of metrics per portfolio per day
        indexes = [
            models.Index(fields=['portfolio', 'date']),
        ]
        unique_together = ['portfolio', 'date']