from django.urls import path
from .views import *
from . import views
urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('forgot-password/', PasswordResetView.as_view(), name='forgot-password'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/', views.get_user_list, name="get_user_list"),
    path('users/<int:pk>/', views.get_user_by_id, name="get_user_by_id"),
    path('users/<int:pk>/update/', views.update_user_by_id, name="update_user_by_id"),
    path('users/<int:pk>/delete/', views.delete_user, name="delete_user"),
    path('users/addresses/', views.user_addresses, name='user-addresses'),
    path('users/addresses/<int:address_id>/', views.user_address_detail, name='user-address-detail'),
    path('user/is_admin/', UserIsAdminView.as_view(), name='user-is-admin')
]