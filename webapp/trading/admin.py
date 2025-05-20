from django.contrib import admin
from .models import Stock, Portfolio, Transaction, StockHolding

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'current_price', 'last_updated')
    search_fields = ('symbol', 'name')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at')
    search_fields = ('user__username',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'transaction_type', 'quantity', 'price', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('user__username', 'stock__symbol')

@admin.register(StockHolding)
class StockHoldingAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'stock', 'quantity')
    search_fields = ('portfolio__user__username', 'stock__symbol')