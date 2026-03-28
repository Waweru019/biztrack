import uuid
from django.db import models
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Profile(models.Model):
    ROLES = (
        ('admin', 'Admin/Owner'),
        ('cashier', 'Cashier'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    business = models.ForeignKey('Business', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default='cashier')
    phone = models.CharField(max_length=15, blank=True, null=True) # Add this line!
    def __str__(self):
        return f"{self.user.username} - {self.role}"

class SubscriptionPlan(models.Model):
    PLAN_INTERVALS = (
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    )

    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(max_length=20, choices=PLAN_INTERVALS)

    def __str__(self):
        return f"{self.name} ({self.interval})"
    
class Business(models.Model):

    BUSINESS_TYPES = (
        ('retail', 'Retail Shop'),
        ('mama_mboga', 'Mama Mboga'),
        ('boda_boda', 'Boda Boda'),
        ('pharmacy', 'Pharmacy'),
        ('electronics', 'Electronics'),
        ('other', 'Other'),
    )

    SUBSCRIPTION_STATUS = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True
    )

 
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default='trial'
    )

    trial_start_date = models.DateTimeField(default=timezone.now)
    trial_end_date = models.DateTimeField(blank=True, null=True)

    subscription_start_date = models.DateTimeField(blank=True, null=True)
    subscription_end_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def activate_subscription(self, plan: SubscriptionPlan):
        """Activate a subscription for this business."""
        self.subscription_plan = plan
        self.subscription_status = "active"
        self.subscription_start_date = timezone.now()

        if plan.interval == "month":
            self.subscription_end_date = self.subscription_start_date + timedelta(days=30)
        elif plan.interval == "quarter":
            self.subscription_end_date = self.subscription_start_date + timedelta(days=90)
        elif plan.interval == "year":
            self.subscription_end_date = self.subscription_start_date + timedelta(days=365)

        self.save()

    def save(self, *args, **kwargs):
        
        if not self.trial_end_date:
            self.trial_end_date = self.trial_start_date + timedelta(days=14)
        super().save(*args, **kwargs)

    def is_trial_active(self):
        return timezone.now() <= self.trial_end_date
    
    def is_subscription_active(self):
     now = timezone.now()
  
    
     if self.subscription_status == 'trial' and self.trial_end_date:
            if now > self.trial_end_date:
                return "expired"
            return "trial"

    
     if self.subscription_status == 'active' and self.subscription_end_date:
            if now > self.subscription_end_date:
                return "expired"
            return "active"
    
     if self.subscription_status in ['cancelled', 'expired']:
        return False

     return False


    def __str__(self):
        return self.name
class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True)   
    abbreviation = models.CharField(max_length=10)        

    def __str__(self):
        return self.abbreviation

from mptt.models import MPTTModel, TreeForeignKey

class Category(MPTTModel):

    BUSINESS_TYPES = [
    ("retail", "Retail"),
    ("boda_boda", "Boda Boda"),
    ("mama_mboga", "Mama Mboga"), 
    ("restaurant", "Restaurant"),
    ("service", "Service"),
    ("other", "Other"), 
     ]
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    business_type = models.CharField(
        max_length=20,
        choices=BUSINESS_TYPES
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    default_unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_service_category = models.BooleanField(default=False)

    class MPTTMeta:
        order_insertion_by = ["name"]
    def save(self, *args, **kwargs):
      if not self.slug:
          self.slug = slugify(self.name)
      super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.business_type})"
    

from django.utils.text import slugify
class Product(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True) 
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    has_bales = models.BooleanField(default=False, help_text="Does this product sell in bales/crates?")
    items_per_bale = models.PositiveIntegerField(default=12, help_text="How many packets in one bale?")
    bale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Discounted price for a full bale"
    )
    is_service = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # AUTOMATION: Check the business type of the owner/business
        if self.business.business_type in ['boda_boda', 'kinyozi']:
            self.is_service = True
            self.stock = 0  # Or keep as 0 since your frontend ignores it
            self.has_bales = False
            
        # Optional: Force "Mama Mboga" or "Retail" to be NOT services by default
        elif self.business.business_type in ['retail', 'hardware']:
            if not self.is_service: # Only force if not manually set
                self.is_service = False
                
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def stock_in_bales(self):
        """Calculates how many full bales are in the store for the dashboard."""
        if self.has_bales and self.items_per_bale > 0:
            return self.stock // self.items_per_bale
        return 0
    
def save(self, *args, **kwargs):
    if not self.sku:
        # Check if category exists, then get its NAME, then slice it
        if self.category and self.category.name:
            prefix = self.category.name[:3].upper()
        else:
            prefix = "GEN"
            
        if not self.pk: 
             import uuid
             self.sku = f"{prefix}-{str(uuid.uuid4())[:8].upper()}"
             
    super().save(*args, **kwargs)

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    total_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Person(models.Model):
    
    TYPE_CHOICES = [('Customer', 'Customer'), ('Supplier', 'Supplier')]
    
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    business = models.ForeignKey('Business', on_delete=models.CASCADE)
    person_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Positive means they owe you, Negative means you owe them

    def __str__(self):
        return f"{self.name} ({self.person_type})"
    
class Sale(models.Model):
    PAYMENT_CHOICES = [
        ("Cash", "Cash"),
        ("M-Pesa", "M-Pesa"),
        ('Credit', 'Credit'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    customer = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(
        max_length=20, 
        choices=[('Paid', 'Paid'), ('Partial', 'Partial'), ('Debt', 'Debt')],
        default='Paid'
    )
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    total_amount = models.FloatField()
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    amount_paid = models.FloatField(null=True, blank=True)
    mpesa_number = models.CharField(max_length=20, blank=True, null=True)
    mpesa_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale {self.id} - {self.business.name}"


class SaleItem(models.Model):
    SALE_MODES = [
        ('single', 'Packet/Single'),
        ('bale', 'Bale/Bulk'),
    ]
    
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField() # Total packets sold
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at which it was sold
    mode = models.CharField(max_length=10, choices=SALE_MODES, default='single')

    def __str__(self):
        return f"{self.product.name} ({self.mode})"

class Expense(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.amount}"
    

    
class UnitConversion(models.Model):
    from_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="conversions_from")
    to_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="conversions_to")
    multiplier = models.DecimalField(max_digits=10, decimal_places=4)  
    # e.g. 1 Bale = 12 Packets → multiplier = 12

    def __str__(self):
        return f"1 {self.from_unit} = {self.multiplier} {self.to_unit}"


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=15)
    balance_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)



class Payment(models.Model):
    customer = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=[('Cash', 'Cash'), ('M-Pesa', 'M-Pesa')])
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Automatically reduce the customer's balance when a payment is saved
        self.customer.balance -= self.amount
        self.customer.save()
        super().save(*args, **kwargs)

import random

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return (timezone.now() - self.created_at).seconds > 300  # 5 mins