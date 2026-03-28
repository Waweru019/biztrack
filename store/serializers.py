# serializers.py
from rest_framework import serializers
from .models import Product,Business,Expense,Sale, SaleItem,Category,Unit,Profile,SubscriptionPlan
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from store.models import Product,Person 
from store.utils import get_user_business
from rest_framework import serializers
from .models import Sale, SaleItem,Payment
from .utils import get_user_business
from django.db import transaction



class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SaleItem
        fields = ["product", "product_name", "quantity", "price", "mode"]

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    customer_name = serializers.ReadOnlyField(source='customer.name')

    class Meta:
        model = Sale
        fields = [
            "id", "items", "total_amount", "payment_method", 
            "amount_paid", "customer", "customer_name", 
            "mpesa_number", "mpesa_code", "status", "balance_due"
        ]
        # We make status and balance_due read_only so the backend calculates them
        read_only_fields = ["status", "balance_due"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        request = self.context.get("request")
        business = get_user_business(request.user)

        # 1. Calculate Debt and Status
        total_amount = validated_data.get("total_amount", 0)
        amount_paid = validated_data.get("amount_paid", 0)
        balance_due = max(0, total_amount - amount_paid)

        if balance_due <= 0:
            status = 'Paid'
        elif amount_paid > 0:
            status = 'Partial'
        else:
            status = 'Debt'

        with transaction.atomic():
            # 2. Create the Sale record
            sale = Sale.objects.create(
                business=business,
                user=request.user,
                status=status,
                balance_due=balance_due,
                **validated_data
            )
            
            # 3. Update Customer Balance if it's a Credit/Partial sale
            customer = validated_data.get("customer")
            if customer and balance_due > 0:
                customer.balance += balance_due
                customer.save()

            # 4. Process individual items
            for item_data in items_data:
                product = item_data["product"]
                mode = item_data.get("mode", "single")
                qty_ordered = item_data["quantity"]

                # Logic for physical stock vs service (Boda trip)
                if not product.is_service:
                    qty_to_subtract = product.items_per_bale if mode == "bale" else qty_ordered
                    
                    if product.stock < qty_to_subtract:
                        raise serializers.ValidationError(
                            f"Insufficient stock for {product.name}. Available: {product.stock}"
                        )
                    
                    product.stock -= qty_to_subtract
                    product.save()

                # Save the line item
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty_ordered,
                    price=item_data["price"],
                    mode=mode
                )

            return sale
class UserRegisterSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField()
    business_type = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "business_name", "business_type", "phone"]
        extra_kwargs = {"password": {"write_only": True}}

    # IMPORTANT: This method MUST be indented inside the class
    def create(self, validated_data):
        # 1. Extract the extra data
        business_name = validated_data.pop("business_name")
        business_type = validated_data.pop("business_type")
        phone = validated_data.pop("phone")

        # 2. Create User (only contains username, email, password now)
        user = User.objects.create_user(**validated_data)

        # 3. Create Business
        business = Business.objects.create(
            owner=user,
            name=business_name,
            business_type=business_type,
            phone=phone,
            email=user.email,
        )

        # 4. Create Profile
        Profile.objects.create(
            user=user,
            business=business,
            role='admin',
            phone=phone
        )

        # 5. Token Generation
        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_abbreviation = serializers.CharField(source="unit.abbreviation", read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'category',          # category id
            'category_name',     # category name
            'unit',              # unit id
            'unit_name',         # unit name
            'unit_abbreviation', # unit abbreviation
            'price',
            'stock',
            'is_service',
        ]
        read_only_fields = ['id']

      
class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)
    default_unit = serializers.PrimaryKeyRelatedField(read_only=True)
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'business_type', 
            'is_service_category', 'level', 'children', 
            "parent",
            'product_count', 'default_unit'
        ]
        read_only_fields = ["slug"]
    

    def get_children(self, obj):
        # This builds the tree: Parent -> Child -> Sub-child
        import store.serializers as s # Avoid circular import
        children = obj.get_children()
        return s.CategorySerializer(children, many=True).data
    
class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name', 'abbreviation']


class ExpenseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Expense
        fields = ["id", "name", "amount", "business",'created_at']
        
        read_only_fields = ['created_at',"business"]
        
from rest_framework import serializers


class SalesPerDaySerializer(serializers.Serializer):
    date = serializers.CharField()
    # Change DecimalField to FloatField
    total = serializers.FloatField() 

class DashboardSerializer(serializers.Serializer):
    name = serializers.CharField()
    subscription_status = serializers.CharField()
    days_remaining = serializers.IntegerField(required=False, allow_null=True)

    # Change all these to FloatField
    today_sales = serializers.FloatField()
    yesterday_sales = serializers.FloatField()
    total_sales = serializers.FloatField()
    week_sales = serializers.FloatField()
    cash_sales = serializers.FloatField()
    mpesa_sales = serializers.FloatField()

    most_sold_product = serializers.CharField()
    most_sold_quantity = serializers.IntegerField()
    today_expenses = serializers.FloatField()
    today_net = serializers.FloatField()
    week_net = serializers.FloatField()
    total_expenses = serializers.FloatField(required=False, default=0.0)

    sales_per_day = SalesPerDaySerializer(many=True)

# store/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['role'] = user.profile.role
        token['business_type'] = user.profile.business.type
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        business = self.user.profile.business

        # Add custom data to the JSON response
        data['role'] = self.user.profile.role
        data['username'] = self.user.username
        data['business_name'] = business.name
        data['business_type'] = business.type  

        # Add trial and subscription info
        data['trial_end_date'] = business.trial_end_date.isoformat() if business.trial_end_date else None
        data['subscription_status'] = business.subscription_status
        data['subscription_valid'] = business.subscription_status == "active" and (
            business.subscription_end_date and business.subscription_end_date >= timezone.now()
        )

        return data


# serializers.py
class StaffCreateSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "role"]

    def create(self, validated_data):
        role = validated_data.pop("role")
        password = validated_data.pop("password")
        
        # 1. Create the User
        user = User.objects.create_user(**validated_data, password=password)
        
        # 2. Get the Admin's business from the context
        request = self.context.get("request")
        admin_business = request.user.profile.business

        # 3. Create the Profile linked to the Admin's business
        Profile.objects.create(
            user=user, 
            business=admin_business, 
            role=role
        )
        return user
    
class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'interval']

from rest_framework import serializers
from .models import Person

# serializers.py
class PersonSerializer(serializers.ModelSerializer):
    # Set business to read_only so it doesn't expect it in the JSON body
    business = serializers.ReadOnlyField(source='business.name')

    class Meta:
        model = Person
        fields = ["id", "name", "phone", "person_type", "business", "balance"]

    

    def validate_phone(self, value):
        """
        Check if the phone number is already registered for this business.
        """
        request = self.context.get('request')
        if not request or not request.user:
            return value

        # Use your helper to get the business
        business = get_user_business(request.user)

        if business:
            # Check if this phone exists ONLY within this specific business
            if Person.objects.filter(phone=value, business=business).exists():
                raise serializers.ValidationError("A customer with this phone number already exists in your records.")
        
        return value
# serializers.py
class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')

    class Meta:
        model = Payment
        fields = ["id", "customer", "customer_name", "amount", "method", "date"]