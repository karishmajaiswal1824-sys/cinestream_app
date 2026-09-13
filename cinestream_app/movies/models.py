import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Genre(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self): return self.name

class Language(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self): return self.name

class City(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Theater(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    def __str__(self): return f"{self.name} ({self.city.name})"

class Movie(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    trailer_url = models.URLField(blank=True, help_text="YouTube Embed URL")
    poster = models.URLField(blank=True)
    age_certification = models.CharField(max_length=10, choices=[('U', 'U'), ('UA', 'U/A'), ('A', 'A'), ('S', 'S')], default='UA')
    duration_minutes = models.IntegerField(default=120)
    genres = models.ManyToManyField(Genre)
    languages = models.ManyToManyField(Language)
    release_date = models.DateField(db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    popularity = models.IntegerField(default=0, db_index=True)
    price = models.IntegerField(help_text="Base ticket price")
    def __str__(self): return self.title

class ShowTiming(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='showtimes')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    show_time = models.DateTimeField(db_index=True)
    def __str__(self): return f"{self.movie.title} - {self.show_time.strftime('%Y-%m-%d %H:%M')}"

class UserHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

class Seat(models.Model):
    show = models.ForeignKey(ShowTiming, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    class Meta: 
        unique_together = ('show', 'seat_number')
        
    def is_available(self):
        if self.is_booked: return False
        if self.locked_until and self.locked_until > timezone.now(): return False
        return True

class Booking(models.Model):
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    show = models.ForeignKey(ShowTiming, on_delete=models.CASCADE)
    seats = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    is_confirmed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    def __str__(self): return str(self.booking_id)

class Payment(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='movie_reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    is_verified_buyer = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)