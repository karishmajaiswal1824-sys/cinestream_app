from django.contrib import admin
from django.db.models import Sum, Count
from django.template.response import TemplateResponse
from django.urls import path
from django.http import HttpResponse
import csv
from .models import Genre, Language, City, Theater, Movie, ShowTiming, UserHistory, Booking, Seat, Payment, Review

class CineStreamAdminSite(admin.AdminSite):
    site_header = "CineStream Analytics Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name="dashboard"),
            path('export-csv/', self.admin_view(self.export_csv), name="export_csv"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum'] or 0
        successful_bookings = Booking.objects.filter(is_confirmed=True).count()
        failed_payments = Payment.objects.filter(status='FAILED').count()
        top_movies = Booking.objects.filter(is_confirmed=True).values('show__movie__title').annotate(bookings=Count('id')).order_by('-bookings')[:5]

        context = dict(
            self.each_context(request),
            total_revenue=total_revenue, successful_bookings=successful_bookings,
            failed_payments=failed_payments, top_movies=top_movies,
        )
        return TemplateResponse(request, "admin/custom_dashboard.html", context)

    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cinestream_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Booking ID', 'Movie', 'User', 'Amount', 'Date', 'Status'])
        for b in Booking.objects.all().select_related('user', 'show__movie').iterator():
            writer.writerow([b.booking_id, b.show.movie.title, b.user.username, b.total_amount, b.created_at, "Confirmed" if b.is_confirmed else "Pending"])
        return response

custom_admin_site = CineStreamAdminSite(name='custom_admin')

custom_admin_site.register(Movie)
custom_admin_site.register(Genre)
custom_admin_site.register(Language)
custom_admin_site.register(City)
custom_admin_site.register(Theater)
custom_admin_site.register(ShowTiming)
custom_admin_site.register(Booking)
custom_admin_site.register(Seat)
custom_admin_site.register(Payment)
custom_admin_site.register(Review)