from .models import Business
import random

def generate_otp():
    return str(random.randint(100000, 999999))

def get_user_business(user):
    return Business.objects.filter(owner=user).first()