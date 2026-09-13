import os
import django
from datetime import timedelta
from django.utils import timezone

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from movies.models import Genre, Language, City, Theater, Movie, ShowTiming

def seed():
    print("Clearing old data...")
    Movie.objects.all().delete()
    City.objects.all().delete()
    Genre.objects.all().delete()
    Language.objects.all().delete()

    print("Creating Genres & Languages...")
    action, _ = Genre.objects.get_or_create(name="Action")
    scifi, _ = Genre.objects.get_or_create(name="Sci-Fi")
    drama, _ = Genre.objects.get_or_create(name="Drama")
    comedy, _ = Genre.objects.get_or_create(name="Comedy")

    english, _ = Language.objects.get_or_create(name="English")
    hindi, _ = Language.objects.get_or_create(name="Hindi")
    kannada, _ = Language.objects.get_or_create(name="Kannada")

    print("Creating Cities & Theaters...")
    blr, _ = City.objects.get_or_create(name="Bengaluru")
    mum, _ = City.objects.get_or_create(name="Mumbai")

    pvr, _ = Theater.objects.get_or_create(name="PVR Cinemas Orion Mall", city=blr)
    inox, _ = Theater.objects.get_or_create(name="INOX Mantri Square", city=blr)
    cinepolis, _ = Theater.objects.get_or_create(name="Cinepolis Andheri", city=mum)

    print("Creating Movies...")
    movie1 = Movie.objects.create(
        title="Inception", release_date="2010-07-16", rating=8.8, popularity=100, price=350
    )
    movie1.genres.add(action, scifi)
    movie1.languages.add(english, hindi)

    movie2 = Movie.objects.create(
        title="The Dark Knight", release_date="2008-07-18", rating=9.0, popularity=95, price=300
    )
    movie2.genres.add(action, drama)
    movie2.languages.add(english)

    movie3 = Movie.objects.create(
        title="3 Idiots", release_date="2009-12-25", rating=8.4, popularity=90, price=200
    )
    movie3.genres.add(comedy, drama)
    movie3.languages.add(hindi)

    movie4 = Movie.objects.create(
        title="KGF: Chapter 2", release_date="2022-04-14", rating=8.3, popularity=98, price=400
    )
    movie4.genres.add(action)
    movie4.languages.add(kannada, hindi)
    
    movie5 = Movie.objects.create(
        title="Interstellar", release_date="2014-11-07", rating=8.6, popularity=92, price=350
    )
    movie5.genres.add(scifi, drama)
    movie5.languages.add(english)

    print("Creating Show Timings...")
    now = timezone.now()
    
    # Add shows for today and tomorrow
    ShowTiming.objects.create(movie=movie1, theater=pvr, show_time=now + timedelta(hours=2))
    ShowTiming.objects.create(movie=movie1, theater=inox, show_time=now + timedelta(hours=5))
    ShowTiming.objects.create(movie=movie2, theater=pvr, show_time=now + timedelta(days=1, hours=1))
    ShowTiming.objects.create(movie=movie3, theater=cinepolis, show_time=now + timedelta(days=1, hours=4))
    ShowTiming.objects.create(movie=movie4, theater=inox, show_time=now + timedelta(hours=3))
    ShowTiming.objects.create(movie=movie5, theater=pvr, show_time=now + timedelta(days=2))

    print("✅ Successfully populated the database with dummy movies, theaters, and showtimes!")

if __name__ == '__main__':
    seed()