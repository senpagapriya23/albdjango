from django.urls import path
# from .views import index
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.admin_login, name='admin_login'),
    path('api/v1/user/add/', views.add_user, name='add_user'),
    path('api/v1/user/delete/<int:user_id>/', views.delete_user, name='delete_user'),    
    path('api/v1/fire_situation/update/<int:batch_id>/', views.update_fire_situation, name='update_fire_situation'),
    path('api/v1/fire_situation/delete/<int:batch_id>/', views.delete_fire_situation, name='delete_fire_situation'),
    
    path('api/v1/login/', views.api_login, name='api_login'),
    path('api/v1/export_data/', views.export_data, name='export_data'),
    path('api/v1/batch/', views.batch, name='batch'),
    path('api/v1/s3_paths/<int:batch_id>/', views.s3_paths, name='s3_paths'),
    path('api/v1/getinfo/<int:batch_id>/', views.get_info, name='get_info'),
    path('api/v1/get_recent_batches/<int:batch_id>/', views.get_recent_batches, name='get_recent_batches'),
    path('api/v1/change_access_code/', views.change_access_code, name='change_access_code'),
    path('api/v1/email/add/', views.add_email, name='add_email'),
    path('api/v1/email/delete/<int:email_id>/', views.delete_email, name='delete_email'),
    path('api/v1/batches/confirm_delete/<str:element_name>/<str:file_type>/<int:batch_id>/', views.confirm_delete, name='confirm_delete'),
]

if settings.DEBUG:
        urlpatterns += static(settings.MEDIA_URL,
                              document_root=settings.MEDIA_ROOT)