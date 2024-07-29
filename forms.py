from django import forms
from django.contrib.auth.models import User
from .models import AccessCode

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput()
        }

class AdminLoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class ShapefileMultipleUploadForm(forms.Form):
    new_files = forms.FileField(label='Upload Shapefile Components', widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}), required=True)

class ImageUploadForm(forms.Form):
    image = forms.ImageField(required=False)
    
class VideoUploadForm(forms.Form):
    video = forms.FileField(required=False)
    
class AccessCodeForm(forms.ModelForm):
    class Meta:
        model = AccessCode
        fields = ['code']
    
class EmailForm(forms.Form):
    email = forms.EmailField()
