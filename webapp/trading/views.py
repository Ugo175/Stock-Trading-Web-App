from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from .models import Stock, Portfolio, Transaction
from .serializers import StockSerializer, PortfolioSerializer
from rest_framework.throttling import UserRateThrottle

class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for viewing stock information.
    Provides 'list' and 'retrieve' actions.
    """
    throttle_classes = [UserRateThrottle]
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'symbol'

class PortfolioViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing user portfolios.
    Includes custom actions for buying and selling stocks.
    """
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return only the authenticated user's portfolio"""
        return Portfolio.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def buy_stock(self, request):
        """Custom endpoint for purchasing stocks"""
        try:
            symbol = request.data.get('symbol')
            quantity = int(request.data.get('quantity'))
            
            stock = get_object_or_404(Stock, symbol=symbol.upper())
            portfolio = self.get_queryset().first()
            
            if portfolio.can_buy_stock(stock, quantity):
                portfolio.buy_stock(stock, quantity)
                return Response({
                    'status': 'success',
                    'message': f'Successfully purchased {quantity} shares of {symbol}'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Insufficient funds for this purchase'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (ValueError, TypeError):
            return Response({
                'status': 'error',
                'message': 'Invalid quantity provided'
            }, status=status.HTTP_400_BAD_REQUEST)

    def handle_exception(self, exc):
        if isinstance(exc, ObjectDoesNotExist):
            return Response(
                {'error': 'Requested resource not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        elif isinstance(exc, ValidationError):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().handle_exception(exc)
