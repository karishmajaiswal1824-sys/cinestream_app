from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('show/<int:show_id>/seats/', views.seat_selection, name='seat_selection'),
    
    # Handles both integer IDs and UUIDs for checkout
    path('checkout/<int:booking_id>/', views.checkout_view, name='checkout_int'),
    path('checkout/<uuid:booking_id>/', views.checkout_view, name='checkout_uuid'),
    
    path('lock-seats/<int:show_id>/', views.lock_seats, name='lock_seats'),
    path('webhook/payment/', views.payment_webhook, name='payment_webhook'),
    path('movie/<int:movie_id>/review/', views.submit_review, name='submit_review'),
    
    # Handles both integer IDs and UUIDs for ticket downloads
    path('ticket/download/<int:booking_id>/', views.download_ticket, name='download_ticket_int'),
    path('ticket/download/<uuid:booking_id>/', views.download_ticket, name='download_ticket_uuid'),
]