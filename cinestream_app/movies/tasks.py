from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from xhtml2pdf import pisa
import qrcode
import base64
from io import BytesIO
from .models import Booking
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_and_send_ticket(self, booking_id):
    try:
        booking = Booking.objects.select_related('user', 'show__movie', 'show__theater').get(id=booking_id)

        # 1. Generate QR Code
        qr = qrcode.make(f"BookingID:{booking.booking_id}|Status:Confirmed")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 2. Render HTML to string
        context = {'booking': booking, 'qr_code': qr_base64}
        html_string = render_to_string('movies/ticket_pdf.html', context)

        # 3. Convert HTML to PDF using xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception("PDF Generation Error")
            
        pdf_file = pdf_buffer.getvalue()

        # 4. Send Email
        subject = f"Your CineStream Ticket - {booking.show.movie.title}"
        message = "Your booking is confirmed! See attached ticket."
        
        email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [booking.user.email])
        email.attach(f"Ticket_{booking.booking_id}.pdf", pdf_file, "application/pdf")
        
        # fail_silently=False ensures the task knows if the email failed so it can retry
        email.send(fail_silently=False)

        return "Success: Email Sent"
        
    except Exception as exc:
        logger.error(f"Email task failed: {exc}")
        # Retry the task after 60 seconds if it fails
        raise self.retry(exc=exc, countdown=60)