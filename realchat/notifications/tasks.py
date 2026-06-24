from celery import shared_task

@shared_task
def send_sms_alert(phone, message):
    # Integrate Twilio here
    print(f"📱 Sending SMS to {phone}: {message}")
    return True