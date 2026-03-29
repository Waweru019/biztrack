# views.py
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework import status,permissions
from .models import Product,Business,Expense, Sale, SaleItem,Profile,Category, Unit,SubscriptionPlan,Person
from .serializers import ProductSerializer,UserRegisterSerializer,SaleSerializer,MyTokenObtainPairSerializer,ExpenseSerializer,StaffCreateSerializer,CategorySerializer, UnitSerializer,PlanSerializer,PersonSerializer
from rest_framework import generics
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.db.models.functions import TruncDate
from .serializers import DashboardSerializer
from .utils import get_user_business
from rest_framework_simplejwt.views import TokenObtainPairView
from .permissions import IsAdminUser
from rest_framework import generics
from django.db import transaction
from rest_framework import serializers
from django.contrib.auth.models import update_last_login
import requests
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SubscriptionPlan, Business
import base64
from rest_framework.decorators import action
from django.utils import timezone
from django.utils import timezone
from django.conf import settings
from requests.auth import HTTPBasicAuth
from datetime import datetime, time
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets




class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

# views.py
@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_staff(request):
    serializer = StaffCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Staff added successfully"}, status=201)
    
    print(serializer.errors) 
    return Response(serializer.errors, status=400)



class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "profile") or request.user.profile.role != "admin":
            return Response({"error": "Admins only"}, status=403)

        business = get_user_business(request.user)

        
        now_nairobi = timezone.localtime(timezone.now())
        
       
        today_start = now_nairobi.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
      
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

       
        today_sales = Sale.objects.filter(
            business=business, 
            created_at__range=(today_start, today_end)
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        yesterday_sales = Sale.objects.filter(
            business=business, 
            created_at__range=(yesterday_start, yesterday_end)
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        total_sales = Sale.objects.filter(
            business=business
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        # 3. Payment Split (For Today)
        cash_sales = Sale.objects.filter(
            business=business, 
            payment_method="Cash",
            created_at__range=(today_start, today_end)
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        mpesa_sales = Sale.objects.filter(
            business=business, 
            payment_method="M-Pesa",
            created_at__range=(today_start, today_end)
        ).aggregate(total=Sum("total_amount"))["total"] or 0
        
        today_expenses = Expense.objects.filter(
            business=business, 
            created_at__range=(today_start, today_end)
        ).aggregate(total=Sum("amount"))["total"] or 0
       
        
        week_start = today_start - timedelta(days=7)
        week_sales_total = Sale.objects.filter(
            business=business,
            created_at__gte=week_start
        ).aggregate(total=Sum("total_amount"))["total"] or 0
# --- 2. Weekly Net ---
        week_sales = Sale.objects.filter(
            business=business,
            created_at__gte=week_start
        ).aggregate(total=Sum("total_amount"))["total"] or 0
        
        week_expenses = Expense.objects.filter(
           business=business, 
           created_at__gte=week_start
         ).aggregate(total=Sum("amount"))["total"] or 0

        week_net = float(week_sales) - float(week_expenses)

        # 4. Graph Logic (Last 8 Days)
        sales_graph = []
        for i in range(7, -1, -1):  # From 7 days ago until today
            day_date = now_nairobi.date() - timedelta(days=i)
            day_start = timezone.make_aware(datetime.combine(day_date, time.min))
            day_end = timezone.make_aware(datetime.combine(day_date, time.max))
            
            day_total = Sale.objects.filter(
                business=business,
                created_at__range=(day_start, day_end)
            ).aggregate(total=Sum("total_amount"))["total"] or 0
            
            sales_graph.append({
                "date": day_date.strftime('%d %b'),
                "total": float(day_total)
            })

        # 5. Top Product
        top_item = SaleItem.objects.filter(sale__business=business).values(
            "product__name"
        ).annotate(total_qty=Sum("quantity")).order_by("-total_qty").first()

        # 6. Response Data
        raw_data = {
            "name": business.name,
            "subscription_status": getattr(business, 'subscription_status', 'trial'),
            "days_remaining": (business.trial_end_date.date() - now_nairobi.date()).days if business.trial_end_date else None,
            "today_sales": float(today_sales),
            "today_net": float(today_sales) - float(today_expenses),
            "yesterday_sales": float(yesterday_sales),
            "total_sales": float(total_sales),
            
            "week_sales": float(week_sales_total),
            "cash_sales": float(cash_sales),
            "mpesa_sales": float(mpesa_sales),
            "most_sold_product": top_item["product__name"] if top_item else "N/A",
            "most_sold_quantity": top_item["total_qty"] if top_item else 0,
            "sales_per_day": sales_graph,
            
            
            "today_expenses": float(today_expenses),
            
            
            "today_expenses": float(today_expenses), 
            "week_net": float(week_net),            
            "total_sales": float(total_sales),
            
        }
        

        serializer = DashboardSerializer(data=raw_data)
        if serializer.is_valid():
            return Response(serializer.data)
       
        return Response(serializer.errors, status=400)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    
    if user is not None:
        if not user.is_active:
            return Response({"error": "Account deactivated."}, status=403)

        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

       
        refresh = RefreshToken.for_user(user)
        
        
        profile = getattr(user, 'profile', None)
        business = profile.business if profile else None
        
        
        role = profile.role if profile else "cashier"
        business_name = business.name if business else "Biztrack"
        
        
        b_type = business.business_type if business else "retail"

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": role,
            "businessName": business_name,
            "business_type": b_type,
            "username": user.username
        }, status=status.HTTP_200_OK)
    
    return Response({"error": "Invalid credentials"}, status=401)

@api_view(['PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_detail(request, pk):
    try:
        business = request.user.profile.business 
    except Business.DoesNotExist:
        return Response({"error": "No business found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        product = Product.objects.get(pk=pk, business=business)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        product.delete()
        return Response({"success": "Product deleted"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_product(request):
    try:
        business = request.user.profile.business 
    except Business.DoesNotExist:
        return Response({"error": "No business found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(business=business) 
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated]) # This allows anyone logged in
def get_products(request):
    try:
        
        business = request.user.profile.business 
        
        if not business:
            return Response({"error": "User is not linked to any business"}, status=404)
            
    except AttributeError:
        return Response({"error": "User profile missing"}, status=404)

   
    products = Product.objects.filter(business=business)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)




class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
       
        user = result["user"]
        business_type = user.profile.business.business_type

        return Response({
            "username": user.username,
            "email": user.email,
            "role": "admin", 
            "businessType": business_type,
            "access": result["access"],
            "refresh": result["refresh"],
        })




class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Expense.objects.filter(business=business)

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(business=business)


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Expense.objects.filter(business=business)

from rest_framework import generics, permissions
from .models import Expense
from .serializers import ExpenseSerializer
from .utils import get_user_business

class ExpenseUpdateView(generics.UpdateAPIView):
    
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Expense.objects.filter(business=business)


class ExpenseDeleteView(generics.DestroyAPIView):
    
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Expense.objects.filter(business=business)



class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    
    def get_queryset(self):
       
        if self.request.query_params.get('roots'):
            return Category.objects.filter(parent=None)
        return Category.objects.all().order_by('tree_id', 'lft') # MPTT sorting
    
class UnitListView(generics.ListAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ["product", "quantity", "price"]



class SaleItemSerializer(serializers.ModelSerializer):
   
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = SaleItem
        fields = ["product", "product_name", "quantity", "price", "mode"]





class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    customer_name = serializers.ReadOnlyField(source='customer.name')
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "items", "total_amount", "payment_method", 
            "amount_paid", "mpesa_number", "mpesa_code", 
            "customer", "customer_name", "created_at"
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        request = self.context["request"]
        business = get_user_business(request.user)

        # 1. Get Sale Info
        customer = validated_data.get("customer")
        payment_method = validated_data.get("payment_method")
        total_amount = validated_data.get("total_amount")
        amount_paid = validated_data.get("amount_paid", 0)

        with transaction.atomic():
            # 2. Create the Sale
            sale = Sale.objects.create(
                business=business,
                user=request.user,
                **validated_data
            )

            # 3. Handle Credit/Debt Logic
            if payment_method == "Credit" and customer:
                # Use str conversion to avoid float precision issues
                debt_to_add = Decimal(str(total_amount)) - Decimal(str(amount_paid))
                
                if debt_to_add > 0:
                    customer.balance += debt_to_add
                    customer.save()

            # 4. Process Items (Stock & SaleItems)
            for item_data in items_data:
                product = item_data["product"]
                mode = item_data.get("mode", "single")
                qty_ordered = item_data["quantity"]
                
                # Logic for stock deduction
                qty_to_sub = product.items_per_bale if mode == "bale" else qty_ordered

                if not product.is_service:
                    if product.stock < qty_to_sub:
                        raise serializers.ValidationError(f"Not enough stock for {product.name}")
                    
                    product.stock -= qty_to_sub
                    product.save()

                # Save the SaleItem record
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty_ordered,
                    price=item_data["price"],
                    mode=mode
                )

            return sale

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer

    def get_queryset(self):
        user_business = get_user_business(self.request.user)
        queryset = Sale.objects.filter(business=user_business).order_by('-created_at')

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        

        if start_date:
            try:
                
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                
                start_dt = timezone.make_aware(datetime.combine(start_dt, time.min))
                queryset = queryset.filter(created_at__gte=start_dt)
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                end_dt = timezone.make_aware(datetime.combine(end_dt, time.max))
                queryset = queryset.filter(created_at__lte=end_dt)
            except (ValueError, TypeError):
                pass

        return queryset

@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def create_sale(request):
    business = get_user_business(request.user)

   
    if request.method == 'GET':
       
        sales = Sale.objects.filter(business=business).order_by('-created_at')
        serializer = SaleSerializer(sales, many=True)
        return Response(serializer.data)

    
    if request.method == 'POST':
        serializer = SaleSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        
        # Log the error to help you debug in the terminal
        print(serializer.errors)
        return Response(serializer.errors, status=400)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_staff_list(request):

    
    if not hasattr(request.user, "profile") or request.user.profile.role != "admin":
        return Response({"error": "Admins only"}, status=403)

    admin_business = request.user.profile.business

    staff_profiles = Profile.objects.filter(
        business=admin_business
    ).select_related('user')

    data = []

    for profile in staff_profiles:
        last_login_formatted = "Never"

        if profile.user.last_login:
            local_time = timezone.localtime(profile.user.last_login)
            last_login_formatted = local_time.strftime("%d %b, %I:%M %p")

        data.append({
            "id": profile.user.id,
            "username": profile.user.username,
            "role": profile.role,
            "is_active": profile.user.is_active,
            "last_login": last_login_formatted
        })

    return Response(data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_staff_status(request, pk):
    
    
    if not hasattr(request.user, "profile") or request.user.profile.role != "admin":
        return Response({"error": "Admins only"}, status=403)

    try:
        admin_business = request.user.profile.business

        profile = Profile.objects.get(
            user_id=pk,
            business=admin_business
        )

        user = profile.user

        
        if user == request.user:
            return Response(
                {"error": "You cannot deactivate your own account."},
                status=400
            )

        
        user.is_active = not user.is_active
        user.save()

        status_label = "activated" if user.is_active else "deactivated"

        return Response({
            "message": f"User {user.username} has been {status_label}.",
            "is_active": user.is_active
        })

    except Profile.DoesNotExist:
        return Response({"error": "Staff member not found."}, status=404)



@api_view(['GET'])
def check_subscription(request):
    user = request.user
    business = user.businesses.first()

    if not business:
        return Response({"is_active": False, "status": "none"})

    now = timezone.now()
    days_remaining = None

    if business.subscription_status == "trial" and business.trial_end_date:
        days_remaining = (business.trial_end_date - now).days
    elif business.subscription_status == "active" and business.subscription_end_date:
        days_remaining = (business.subscription_end_date - now).days

    return Response({
        "is_active": business.is_subscription_active(),
        "status": business.subscription_status,   # trial, active, expired, cancelled
        "trial_end_date": business.trial_end_date,
        "subscription_end_date": business.subscription_end_date,
        "days_remaining": days_remaining,
    })
    
class PlanListView(generics.ListAPIView):
    queryset =SubscriptionPlan.objects.all()
    serializer_class = PlanSerializer




# Configuration (In production, use environment variables)
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
MPESA_CONSUMER_KEY = "crRK8TJbMyKYnRFs6k6qnaxw1MJ9q3T6G4oJ2ho57dEPaAaj"
MPESA_CONSUMER_SECRET = "oNC9A2WyU7Mf4zkK0o08L5sXOfjUkYGKRc4bPHwOJrvJCa3PAG3caozL2Q8xmKWF"

def get_mpesa_token():
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(auth_url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Token Error: {e}")
        return None

@api_view(['POST'])
def subscribe(request):
    user = request.user
    # Ensure business exists
    business = user.businesses.first()
    if not business:
        return Response({"error": "No business found for this user"}, status=404)

    plan_id = request.data.get("plan_id")
    phone = request.data.get("phone")

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({"error": "Invalid plan"}, status=400)

    token = get_mpesa_token()
    if not token:
        return Response({"error": "Internal server error (Auth)"}, status=500)

    # 1. Generate syncronized Timestamp and Password
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    data_to_encode = MPESA_SHORTCODE + MPESA_PASSKEY + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode()

    # 2. Prepare Payload
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(plan.price), # Ensure it's an integer for Sandbox
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE, 
        "PhoneNumber": phone,
        "CallBackURL": "https://unbragging-conchita-superadjacent.ngrok-free.dev/api/mpesa/callback/",
        "AccountReference": f"Biztrack-waweru dan", 
        "TransactionDesc": f"Pay {plan.name}"
    }

    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.post(stk_url, json=payload, headers=headers)
        res_data = res.json()
        
        if res.status_code == 200:
            return Response({
                "message": "Payment prompt sent to phone",
                "CheckoutRequestID": res_data.get("CheckoutRequestID")
            })
        return Response({"error": res_data.get("errorMessage", "Request failed")}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def mpesa_callback(request):
    data = request.data
    stk_callback = data.get("Body", {}).get("stkCallback", {})
    result_code = stk_callback.get("ResultCode")
    checkout_id = stk_callback.get("CheckoutRequestID")

   
    print(f"Callback received for {checkout_id}. Result: {result_code}")

    if result_code == 0:
        items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    return Response({"ResultCode": 1, "ResultDesc": "Failed"})



class CategoryCreateView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # If parent is provided, validate it
        parent_id = data.get("parent")
        if parent_id:
            try:
                parent = Category.objects.get(id=parent_id)
                data["parent"] = parent.id
            except Category.DoesNotExist:
                return Response(
                    {"error": "Parent category not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # No parent → this will be a new top-level category
            data["parent"] = None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)




# views.py
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def person_list_create(request):
    # Use the helper instead of direct attribute access
    business = get_user_business(request.user) 

    if not business:
        return Response({"error": "User is not associated with any business."}, status=403)

    if request.method == "GET":
        people = Person.objects.filter(business=business).order_by('name')
        serializer = PersonSerializer(people, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        # Pass request in context so serializer can use it for validation
        serializer = PersonSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Explicitly save with the business we found
            serializer.save(business=business) 
            return Response(serializer.data, status=201)
        
        return Response(serializer.errors, status=400)




class PeopleViewSet(viewsets.ModelViewSet):
    
     queryset = Person.objects.all()
     queryset = Person.objects.all() 
     serializer_class = PersonSerializer

   
     def get_queryset(self):
        user_business = get_user_business(self.request.user)
        return Person.objects.filter(business=user_business)

     @action(detail=True, methods=['post'])
     def pay_debt(self, request, pk=None):
        customer = self.get_object()
        amount = Decimal(request.data.get('amount', 0))
        method = request.data.get('method', 'Cash') # Cash or M-Pesa

        if amount <= 0:
            return Response({"error": "Invalid amount"}, status=400)

        with transaction.atomic():
            # 1. Reduce the balance
            customer.balance -= amount
            customer.save()

            

            return Response({
                "message": "Payment successful",
                "new_balance": str(customer.balance)
            })

# views.py
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import PasswordResetOTP
from .utils import generate_otp

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get("email")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    otp = generate_otp()

    # Save OTP
    PasswordResetOTP.objects.create(user=user, otp=otp)

    # Send Email
    subject = "Password Reset OTP"
    message = f"Your OTP is {otp}. It expires in 5 minutes."  
    html_message = f"""
<div style="font-family: Arial; padding: 20px; background: #0f172a; color: white;">
    <h2 style="color: #6366f1;">Biztrack Password Reset</h2>
    
    <p>Your OTP code is:</p>
    
    <h1 style="
        background: #1e293b;
        padding: 15px;
        text-align: center;
        border-radius: 10px;
        letter-spacing: 5px;
        color: #10b981;
    ">
        {otp}
    </h1>
    
    <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">
        This code expires in 5 minutes.
    </p>
</div>
"""
    send_mail(
        subject,
        message,  
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],                   
        fail_silently=False,
        html_message=html_message     
    )


    return Response({"message": "OTP sent to email"})

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get("email")
    otp = request.data.get("otp")
    new_password = request.data.get("new_password")

    try:
        user = User.objects.get(email=email)
        otp_record = PasswordResetOTP.objects.filter(user=user, otp=otp).last()
    except:
        return Response({"error": "Invalid request"}, status=400)

    if not otp_record:
        return Response({"error": "Invalid OTP"}, status=400)

    if otp_record.is_expired():
        return Response({"error": "OTP expired"}, status=400)

   
    user.set_password(new_password)
    user.save()

   
    otp_record.delete()

    return Response({"message": "Password reset successful"})