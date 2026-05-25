from django.contrib import admin

from .models import Category, Customer, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku")
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "phone", "created_at")
    search_fields = ("full_name", "user__username", "phone")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "customer", "status", "total", "placed_at", "paid_at", "shipped_at")
    list_filter = ("status",)
    search_fields = ("customer__full_name", "customer__user__username")
    autocomplete_fields = ("customer",)
    readonly_fields = ("placed_at", "total")
    date_hierarchy = "placed_at"

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.status in {
            obj.Status.PAID,
            obj.Status.SHIPPED,
            obj.Status.DELIVERED,
        }:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_price")
    search_fields = ("order__pk", "product__name", "product__sku")
    autocomplete_fields = ("order", "product")
