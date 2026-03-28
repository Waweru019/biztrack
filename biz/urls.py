"""
URL configuration for biz project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import path
from store import views
from store.views import RegisterView,DashboardView,ExpenseUpdateView,ExpenseDeleteView,ExpenseListCreateView,ExpenseDetailView,SaleViewSet,CategoryListView,UnitListView,PlanListView,PeopleViewSet, CategoryCreateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    path('api/products/create/', views.create_product),
    path('api/products/<int:pk>/', views.product_detail, name='delete-product'),
    path("api/products/", views.get_products),
    path("api/categories/", CategoryListView.as_view(), name="categories"),
    path("api/categories/create/", CategoryCreateView.as_view(), name="categoriescreate"),
    path("api/units/", UnitListView.as_view() , name="units"),
     path("api/register/", RegisterView.as_view(), name="register"), 
      path("api/login/", views.login_view, name="login"),
      path("api/request_password/", views.request_password_reset, name="login"),
      path("api/reset_password/", views.reset_password, name="login"),
      
 
     path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
     path("api/dashboard/", DashboardView.as_view(), name="dashboard"), 
      path("api/expenses/", ExpenseListCreateView.as_view(), name="expense-list-create"),
      path("api/expenses/<int:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
     path('api/expenses/<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense-update'),
      path('api/expenses/<int:pk>/delete/', ExpenseDeleteView.as_view(), name='expense-delete'),
    path("api/sales/", views.create_sale, name="sales"),
    
     path("api/sales/", SaleViewSet.as_view({'get': 'list', 'post': 'create'}), name="sales"),
    
    path("api/add/", views.add_staff, name="add"),
    path("api/staff/", views.get_staff_list, name="staff"),
    path("api/staff/toggle/<int:pk>/", views.toggle_staff_status, name="staff"),
    path("api/subscription/", views.check_subscription, name="subscription"),
    path("api/plans/", PlanListView.as_view(), name="plans"),
    path("api/subscribe/", views.subscribe, name="subscribe"),
    path("api/people/", views.person_list_create, name="people"),
    path("api/people/",  PeopleViewSet.as_view({'get': 'list', 'post': 'create'}), name="sales"),
    path("api/people/<int:pk>/pay_debt/", PeopleViewSet.as_view({'post': 'pay_debt'}), name="person-pay-debt"),
    
    
   
    
  
    
   
    
]
