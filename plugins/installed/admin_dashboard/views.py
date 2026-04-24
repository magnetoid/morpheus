from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from api.client import internal_graphql

# Law 3: The dashboard never touches the ORM. It consumes the GraphQL API.

DASHBOARD_QUERY = """
query DashboardOverview {
  metrics {
    totalRevenue { amount currency }
    totalOrders
    activeCustomers
    revenueGrowthPercentage
  }
  recentOrders: orders(first: 5, orderBy: "-createdAt") {
    id orderNumber status total { amount currency } customer { email fullName } createdAt
  }
  merchantInsights(unread: true, first: 3) {
    id title body priority suggestedAction { type }
  }
}
"""

@staff_member_required
def dashboard_home(request):
    data = internal_graphql(DASHBOARD_QUERY, request=request)
    return render(request, 'admin_dashboard/home.html', {
        'data': data or {},
        'active_nav': 'home',
    })

@staff_member_required
def products_list(request):
    data = internal_graphql("""
        query { products(first: 50) { id name sku price { amount } status isFeatured } }
    """, request=request)
    return render(request, 'admin_dashboard/products.html', {'data': data, 'active_nav': 'products'})

@staff_member_required
def orders_list(request):
    data = internal_graphql("""
        query { orders(first: 50, orderBy: "-createdAt") { id orderNumber status total { amount } } }
    """, request=request)
    return render(request, 'admin_dashboard/orders.html', {'data': data, 'active_nav': 'orders'})

@staff_member_required
def customers_list(request):
    data = internal_graphql("""
        query { customers(first: 50) { id email fullName totalSpent { amount } } }
    """, request=request)
    return render(request, 'admin_dashboard/customers.html', {'data': data, 'active_nav': 'customers'})

@staff_member_required
def ai_insights(request):
    data = internal_graphql("""
        query { merchantInsights(first: 50) { id title body priority isApproved aiExecuted createdAt } }
    """, request=request)
    return render(request, 'admin_dashboard/ai_insights.html', {'data': data, 'active_nav': 'ai_insights'})
