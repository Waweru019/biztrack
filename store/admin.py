from django.contrib import admin
from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from .models import Product,Business,Expense,SaleItem,Sale,Category,Unit,UnitConversion,SubscriptionPlan,Person,Profile,Customer

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ('tree_actions', 'indented_title', 'default_unit')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register (Product)
admin.site.register (Business)
admin.site.register(Expense)
admin.site.register(SaleItem)
admin.site.register(Sale)
admin.site.register(UnitConversion)
admin.site.register(Unit)
admin.site.register(SubscriptionPlan)
admin.site.register(Person)
admin.site.register(Customer)
admin.site.register(Profile)



# Register your models here.
