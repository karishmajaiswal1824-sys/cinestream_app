from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
from xhtml2pdf import pisa
import qrcode
import base64
import json
from io import BytesIO

from .models import Movie, Genre, Language, City, Theater, ShowTiming, UserHistory, Booking, Seat, Payment, Review
from .tasks import generate_and_send_ticket
from django.views.decorators.csrf import csrf_exempt

def home(request):
    """ Handles the main discovery page with search, filters, pagination, and recommendations. """
    movies = Movie.objects.prefetch_related('genres', 'languages', 'showtimes').all()
    
    # 1. Search and Filtering
    search = request.GET.get('search')
    genre_id = request.GET.get('genre')
    
    if search: 
        movies = movies.filter(title__icontains=search)
    if genre_id: 
        movies = movies.filter(genres__id=genre_id)
        
    # 2. Sorting Logic
    sort_by = request.GET.get('sort', '-popularity')
    valid_sorts = {
        'popularity': '-popularity',
        'newest': '-release_date',
        'rating': '-rating'
    }
    movies = movies.distinct().order_by(valid_sorts.get(sort_by, '-popularity'))

    # 3. Handle AJAX count requests
    matching_count = movies.count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'count': matching_count})

    # 4. Pagination (6 movies per page)
    paginator = Paginator(movies, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 5. Recommendation Engine (Based on user history or fallback to popularity)
    recommended = []
    if request.user.is_authenticated:
        user_history = UserHistory.objects.filter(user=request.user).values_list('movie__genres', flat=True)
        if user_history:
            recommended = Movie.objects.filter(genres__in=user_history).exclude(userhistory__user=request.user).distinct()[:4]
    
    if not recommended:
        recommended = Movie.objects.order_by('-popularity')[:4]

    context = {
        'page_obj': page_obj, 
        'count': matching_count,
        'recommended_movies': recommended, 
        'genres': Genre.objects.all(),
    }
    return render(request, 'movies/index.html', context)


def seat_selection(request, show_id):
    """ Renders the visual seat map showing available, locked, and booked seats. """
    show = get_object_or_404(ShowTiming, id=show_id)
    now = timezone.now()
    
    # Fetch current state of seats from DB
    booked_seats = Seat.objects.filter(show=show, is_booked=True).values_list('seat_number', flat=True)
    locked_seats = Seat.objects.filter(show=show, locked_until__gt=now, is_booked=False).values_list('seat_number', flat=True)
    
    # Construct the visual grid layout (A1 to F10)
    seat_map = []
    for row in ['A', 'B', 'C', 'D', 'E', 'F']:
        seat_row = []
        for col in range(1, 11):
            num = f"{row}{col}"
            status = 'available'
            if num in booked_seats:
                status = 'booked'
            elif num in locked_seats:
                status = 'locked'
            seat_row.append({'number': num, 'status': status})
        seat_map.append({'row': row, 'seats': seat_row})
        
    return render(request, 'movies/seats.html', {'show': show, 'seat_map': seat_map})


@csrf_exempt
@transaction.atomic
def lock_seats(request, show_id):
    """ Handles concurrent booking via select_for_update and locks seats temporarily. """
    if request.method == 'POST':
        data = json.loads(request.body)
        requested_seats = data.get('seats', [])
        show = get_object_or_404(ShowTiming, id=show_id)
        
        # Determine the user (fallback to guest if not logged in)
        if request.user.is_authenticated:
            user = request.user
        else:
            user, created = User.objects.get_or_create(username='guest', email='guest@test.com')

        # 1. Ensure Seat objects exist before we attempt to lock them
        for seat_num in requested_seats:
            Seat.objects.get_or_create(show=show, seat_number=seat_num)

        # 2. Lock the specific rows in the database (prevents duplicate bookings)
        seats = Seat.objects.select_for_update().filter(show=show, seat_number__in=requested_seats)
        
        # 3. Check if they are still available
        for seat in seats:
            if not seat.is_available(): 
                return JsonResponse({"error": f"Seat {seat.seat_number} is already taken!"}, status=400)

        # 4. Lock them for 2 minutes
        lock_time = timezone.now() + timedelta(minutes=2)
        for seat in seats:
            seat.locked_until = lock_time
            seat.save()

        # 5. Generate unconfirmed booking
        booking = Booking.objects.create(
            user=user, 
            show=show, 
            seats=",".join(requested_seats),
            total_amount=show.movie.price * len(requested_seats), 
            is_confirmed=False
        )
        return JsonResponse({"status": "success", "booking_id": str(booking.id)})


def checkout_view(request, booking_id):
    """ Renders the mock payment gateway screen. """
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'movies/checkout.html', {'booking': booking})


@csrf_exempt
def payment_webhook(request):
    """ Verifies the simulated payment webhook and finalizes the booking/ticket. """
    if request.method == 'POST':
        data = json.loads(request.body)
        booking = get_object_or_404(Booking, id=data.get('booking_id'))
        seat_list = booking.seats.split(",")

        if data.get('status') == 'SUCCESS':
            # Create successful payment record
            Payment.objects.create(transaction_id=data.get('transaction_id'), booking=booking, amount=booking.total_amount, status='SUCCESS')
            
            # Confirm booking and permanently reserve seats
            booking.is_confirmed = True
            booking.save()
            Seat.objects.filter(show=booking.show, seat_number__in=seat_list).update(is_booked=True, locked_until=None)
            
            # Trigger background celery task to generate and email PDF
            generate_and_send_ticket.delay(booking.id)
            
            return JsonResponse({"message": "Payment successful! Your ticket is generating."})
        else:
            # Payment failed, release the locked seats
            Payment.objects.create(transaction_id=data.get('transaction_id'), booking=booking, amount=booking.total_amount, status='FAILED')
            Seat.objects.filter(show=booking.show, seat_number__in=seat_list).update(locked_until=None)
            
            return JsonResponse({"message": "Payment failed. Seats released."})


def submit_review(request, movie_id):
    """ Allows a user to review a movie only if they have successfully booked it. """
    if request.method == 'POST':
        movie = get_object_or_404(Movie, id=movie_id)
        
        if not request.user.is_authenticated: 
            return JsonResponse({"error": "Must be logged in to review."}, status=401)
            
        # Verify the user is a confirmed buyer for this movie
        has_booked = Booking.objects.filter(user=request.user, show__movie=movie, is_confirmed=True).exists()
        if not has_booked:
            return JsonResponse({"error": "You can only review movies you have booked!"}, status=403)

        # Save the review
        Review.objects.create(
            movie=movie, 
            user=request.user, 
            rating=request.POST.get('rating'), 
            comment=request.POST.get('comment'), 
            is_verified_buyer=True
        )
        
        # Recalculate average rating for the movie
        avg_rating = movie.movie_reviews.aggregate(Avg('rating'))['rating__avg']
        movie.rating = round(avg_rating, 1) if avg_rating else 0
        movie.save()
        
        return JsonResponse({"message": "Review added successfully!"})


def download_ticket(request, booking_id):
    """ Renders and returns the PDF ticket for download. """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Generate QR Code dynamically
    qr = qrcode.make(f"BookingID:{booking.booking_id}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Render HTML and convert to PDF using xhtml2pdf
    html_string = render_to_string('movies/ticket_pdf.html', {'booking': booking, 'qr_code': qr_base64})
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html_string, dest=pdf_buffer)
    
    # Return file response
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ticket_{booking.booking_id}.pdf"'
    return response