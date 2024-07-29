from django.contrib import admin
from .models import Batch,ShpMetadata,VideoMetadata,ImageMetadata
# from django.contrib.auth.models import User
# Register your models here.
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

admin.site.register(Batch)
admin.site.register(ShpMetadata)
admin.site.register(ImageMetadata)
admin.site.register(VideoMetadata)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)