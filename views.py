from django.shortcuts import render,redirect, get_object_or_404
from .models import Batch, ShpMetadata, ImageMetadata, VideoMetadata,AccessCode,EmailList
from .forms import ShapefileMultipleUploadForm, ImageUploadForm, VideoUploadForm,AdminLoginForm,UserForm,AccessCodeForm,EmailForm 
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.conf import settings
from django.http import HttpResponse,HttpResponseBadRequest,JsonResponse
from django.urls import reverse
import requests
import boto3
import os
import tempfile,zipfile,shutil
import io
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .serializers import BatchSerializer, ShpMetadataSerializer, ImageMetadataSerializer, VideoMetadataSerializer
from datetime import timedelta
from django.contrib import messages

s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)
api_key = "5c4b838e17ca43749d14bc52088723df"

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            form = AccessCodeForm(data)
            
            if form.is_valid():
                entered_code = form.cleaned_data['code']
                if AccessCode.objects.filter(code=entered_code).exists():
                    return JsonResponse({'status': 'success', 'message': 'Login successful'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Invalid access code.'}, status=400)
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid form data.'}, status=400)
    
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid request format.'}, status=400)
        
    #     data = json.loads(request.body.decode('utf-8'))
    #     print(data)
    #     username = data.get('username')
    #     password = data.get('password')
    #     print(username,password)
    #     user = authenticate(username=username, password=password)
    #     if user is not None:
    #         login(request, user)
    #         return JsonResponse({'status': 'success', 'message': 'Login successful'})
    #     else:
    #         return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=400)
    # return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                form.add_error(None, 'Invalid username or password.')
    else:
        form = AdminLoginForm()
    
    return render(request, 'admin_login.html', {'form': form})

def add_user(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect(reverse('index') + '?redirect=systemConnection')
    else:
        form = UserForm()
        
    users = User.objects.all()
    
    return render(request, 'index.html', {'form': form, 'users': users})

def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return redirect(reverse('index') + '?redirect=systemConnection')

def index(request):
    if not request.user.is_authenticated:
        return redirect('admin_login')
    
    try:
        data = []
        status_options = set()
        tag_options = set()
        element_format_options = set()

        if request.method == "POST":
            print("post")
            zip_code = request.POST.get("zip_code")
            status = request.POST.get("status")
            tag = request.POST.get("tag")
            element_format = request.POST.get("element_format")
            fromdate = request.POST.get("fromdate")
            todate = request.POST.get("todate")
            
            if tag:
                batches = Batch.objects.filter(tags=tag)            
            elif status:
                batches = Batch.objects.filter(status=status)
                print(batches)
            elif fromdate and todate:
                batches = Batch.objects.filter(acquisition_date__range=[fromdate, todate])
            else:
                batches = Batch.objects.all().order_by("-id")

        else:
            batches = Batch.objects.all().order_by("-id")

        for batch in batches:
            fire_situation = {
                "id": batch.id,
                "status": batch.status,
                "unique_reference": [],
                "batch_name": batch.batch_name,
                "elements": [],
                "tags": batch.tags
            }

            if request.method == "POST" and element_format:
                shp_metadata = ShpMetadata.objects.filter(batch_id=batch.id).first()
                if shp_metadata:
                    geom = shp_metadata.geom
                    centroid = geom.centroid
                    
                    zipcode = get_zipcode_from_coordinates(centroid.y, centroid.x)
                    fire_situation["unique_reference"].append({"gps_coords": [centroid.y,centroid.x]})
                    if zipcode:
                        fire_situation["unique_reference"].append({"zipcode": zipcode})
                    print(fire_situation["unique_reference"])
                        
                if element_format == "Shapefile":
                    shp_metadata = ShpMetadata.objects.filter(batch_id=batch.id).first()
                    if shp_metadata:
                        fire_situation["elements"].append({"element_type": "Shapefile", "name": shp_metadata.file_name})

                elif element_format == "Image":
                    img_metadata_list = ImageMetadata.objects.filter(batch_id=batch.id)
                    for img_metadata in img_metadata_list:
                        fire_situation["elements"].append({"element_type": "Image", "name": img_metadata.file_name})

                elif element_format == "Video":
                    video_metadata = VideoMetadata.objects.filter(batch_id=batch.id).first()
                    if video_metadata:
                        fire_situation["elements"].append({"element_type": "Video", "name": video_metadata.file_name})

            else:                
                shp_metadata = ShpMetadata.objects.filter(batch_id=batch.id).first()
                if shp_metadata:
                    fire_situation["elements"].append({"element_type": "Shapefile", "name": shp_metadata.file_name})
                    geom = shp_metadata.geom
                    centroid = geom.centroid
                    
                    zipcode = get_zipcode_from_coordinates(centroid.y, centroid.x)
                    fire_situation["unique_reference"].append({"gps_coords": [centroid.y,centroid.x]})
                    if zipcode:
                        fire_situation["unique_reference"].append({"zipcode": zipcode})
                    print(fire_situation["unique_reference"])

                img_metadata_list = ImageMetadata.objects.filter(batch_id=batch.id)
                for img_metadata in img_metadata_list:
                    fire_situation["elements"].append({"element_type": "Image", "name": img_metadata.file_name})

                video_metadata = VideoMetadata.objects.filter(batch_id=batch.id).first()
                if video_metadata:
                    fire_situation["elements"].append({"element_type": "Video", "name": video_metadata.file_name})
                    
                if shp_metadata:    
                    fire_situation["elements"].append({"element_type": "Fire area", "name": float(shp_metadata.fire_area)})
                    if shp_metadata.fire_propagation == None:
                        shp_metadata.fire_propagation = 'null'
                        shp_metadata.fire_orientation = 'null'
                    fire_situation["elements"].append({"element_type": "Fire Propagation","name": shp_metadata.fire_propagation})
                    fire_situation["elements"].append({"element_type": "Fire Orientation", "name": shp_metadata.fire_orientation})

            data.append(fire_situation)
            
        for status in ["ONGOING","ENDED"]:
            status_options.add(status)

        for tag in ["Lab", "Field", "OP"]:
            tag_options.add(tag)

        for element in ["Shapefile","Image","Video"]:                
            element_format_options.add(element)
                
            # for element in fire_situation["elements"]:
            #     if "element_type" in element:
            #         if element["element_type"] not in ["Fire area", "Fire Propagation", "Fire Orientation"]:
            #             element_format_options.add(element["element_type"])
            
        form = UserForm()
        users = User.objects.all()
        
        email_form = EmailForm()
        emails = EmailList.objects.all()
        access_code = AccessCode.objects.first()

        return render(request, "index.html", {
            "data": data,
            "status_options": status_options,
            "tag_options": tag_options,
            "element_format_options": element_format_options,
            "form": form,
            "users": users,
            'email_form': email_form,
            'emails': emails,
            'access_code':access_code,
        })

    except Exception as error:
        print(error)
        return render(request, "index.html", {"data": []})

def handle_multiple_files_upload(files, batch):
    required_files = {".dbf",".prj",".shp",".shx"}
    uploaded_files = set()
    tempdir = tempfile.mkdtemp()
    
    try:
        for new_file in files:
            file_extension = os.path.splitext(new_file.name)[1]
            if file_extension in required_files:
                file_path = os.path.join(tempdir, new_file.name)
                with open(file_path, 'wb+') as destination:
                    for chunk in new_file.chunks():
                        destination.write(chunk)
                uploaded_files.add(file_extension)
        
        if not required_files.issubset(uploaded_files):
            return False, "All .prj, .dbf, .shx, and .shp files must be uploaded."
        
        for file in os.listdir(tempdir):
            file_path = os.path.join(tempdir, file)
            s3.upload_file(file_path, settings.AWS_STORAGE_BUCKET_NAME, f"shapefiles/{file}")
            print(f'Uploaded {file} to {settings.AWS_STORAGE_BUCKET_NAME}')
        
        # Clean up old files
        base_name = os.path.splitext(os.path.basename(files[0].name))[0]
        for ext in [".dbf",".prj",".shp",".shx"]:
            s3_key = f"shapefiles/{base_name}{ext}"
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
            print(f'Deleted {s3_key} from {settings.AWS_STORAGE_BUCKET_NAME}')
        
        ShpMetadata.objects.filter(batch=batch, file_name=base_name).delete()
        return True, None
    
    except Exception as e:
        return False, str(e)
    
    finally:
        shutil.rmtree(tempdir)


def handle_file_upload(file, file_type, batch, element_name):
    s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME, f"{file_type}/{file}")
    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=f"{file_type}/{element_name}")

    if file_type == "images":
        ImageMetadata.objects.filter(batch=batch, file_name=element_name).delete()
    elif file_type == "videos":
        VideoMetadata.objects.filter(batch=batch, file_name=element_name).delete()

def update_fire_situation(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    element_type = request.POST.get("element_type")    
    print("Filterd element_type:",element_type)
    
    shp_metadata = ShpMetadata.objects.filter(batch=batch).first()
    geom = shp_metadata.geom if shp_metadata else None
    centroid = geom.centroid if geom else None
    zipcode = get_zipcode_from_coordinates(centroid.y, centroid.x) if centroid else None
    
    shp_metadata = None
    image_metadata = None
    video_metadata = None
    image_metadata_count = 0
    video_metadata_count = 0
    shp_metadata_count = 0 
    
    fire_situation = {
        "elements": []
    }
        
    if element_type == "Image":
        image_metadata = ImageMetadata.objects.filter(batch=batch)
        image_metadata_count = image_metadata.count()
        for img_ in image_metadata:
            fire_situation["elements"].append({"element_type": "Image","name": img_.file_name})
    elif element_type == "Video":
        video_metadata = VideoMetadata.objects.filter(batch=batch).first()
        video_metadata_count = 1
        fire_situation["elements"].append({"element_type": "Video","name": video_metadata.file_name})
    elif element_type == "Shapefile":
        shp_metadata = ShpMetadata.objects.filter(batch=batch).first()
        shp_metadata_count = 1
        fire_situation["elements"].append({"element_type": "Shapefile","name": shp_metadata.file_name})        
    else:           
        image_metadata = ImageMetadata.objects.filter(batch=batch)
        shp_metadata = ShpMetadata.objects.filter(batch=batch).first()
        video_metadata = VideoMetadata.objects.filter(batch=batch).first()
        image_metadata_count = image_metadata.count()
        video_metadata_count = 1
        shp_metadata_count = 1
        fire_situation["elements"].append({"element_type": "Shapefile","name": shp_metadata.file_name}) 
        for img_ in image_metadata:
            fire_situation["elements"].append({"element_type": "Image","name": img_.file_name})
        fire_situation["elements"].append({"element_type": "Video","name": video_metadata.file_name})

    shapefile_zip_form = ShapefileMultipleUploadForm()
    image_form = ImageUploadForm()
    video_form = VideoUploadForm()

    if request.method == "POST":
        if "update_batch" in request.POST:
            update_batch_details(request, batch)
        
        elif "update_shapefile" in request.POST:
            shapefile_form = ShapefileMultipleUploadForm(request.POST, request.FILES)
            if shapefile_form.is_valid():
                files = request.FILES.getlist('new_files')
                success, error = handle_multiple_files_upload(files, batch)
                if success:
                    return redirect("update_fire_situation", batch_id=batch_id)
                else:
                    shapefile_form.add_error(None, error)

        elif "update_image" in request.POST:
            element_name = request.POST['update_image']
            image_form = ImageUploadForm(request.POST, request.FILES)
            if image_form.is_valid():
                handle_file_upload(image_form.cleaned_data["image"], "images", batch, element_name)
                return redirect("update_fire_situation", batch_id=batch_id)

        elif "update_video" in request.POST:
            element_name = request.POST['update_video']
            video_form = VideoUploadForm(request.POST, request.FILES)
            if video_form.is_valid():
                handle_file_upload(video_form.cleaned_data["video"], "videos", batch, element_name)
                return redirect("update_fire_situation", batch_id=batch_id)

        elif "delete_shapefile" in request.POST:            
            element_name = request.POST['delete_shapefile']
            # handle_file_deletion(element_name, "shapefiles", ShpMetadata, batch)
            return redirect('confirm_delete', element_name=element_name, file_type="shapefiles", batch_id=batch_id)

        elif "delete_image" in request.POST:            
            element_name = request.POST['delete_image']
            # handle_file_deletion(element_name, "images", ImageMetadata, batch)
            return redirect('confirm_delete', element_name=element_name, file_type="images", batch_id=batch_id)
            # return render(request, "confirm_delete.html", {'element_name':element_name, 'file_type':"images", 'batch_id':batch_id})

        elif "delete_video" in request.POST:
            element_name = request.POST['delete_video']
            # handle_file_deletion(element_name, "videos", VideoMetadata, batch)
            return redirect('confirm_delete', element_name=element_name, file_type="videos", batch_id=batch_id)
            
        elif "add_files" in request.POST:
            new_file = request.FILES.get('new_file')
            files = request.FILES.getlist('new_files')
            if new_file:
                print(new_file.name,new_file.content_type) 
                
                if new_file.content_type.startswith('image/'):
                    image_form = ImageUploadForm(request.POST, request.FILES)
                    if image_form.is_valid():
                        s3.upload_fileobj(new_file, settings.AWS_STORAGE_BUCKET_NAME, f"images/{new_file}")
                        return redirect("update_fire_situation", batch_id=batch_id)
                            
                elif new_file.content_type.startswith('video/'):
                    video_form = VideoUploadForm(request.POST, request.FILES)
                    if video_form.is_valid():                        
                        s3.upload_fileobj(new_file, settings.AWS_STORAGE_BUCKET_NAME, f"images/{new_file}")
                        return redirect("update_fire_situation", batch_id=batch_id)
                    
            if files:
                files = request.FILES.getlist('new_files')
                required_files = {".dbf",".prj",".shp",".shx"}
                uploaded_files = set()
                tempdir = tempfile.mkdtemp()

                for new_file in files:
                    file_extension = os.path.splitext(new_file.name)[1]
                    if file_extension in required_files:
                        file_path = os.path.join(tempdir, new_file.name)
                        with open(file_path, 'wb+') as destination:
                            for chunk in new_file.chunks():
                                destination.write(chunk)
                        uploaded_files.add(file_extension)
                        
                if not required_files.issubset(uploaded_files):
                    shapefile_zip_form = ShapefileMultipleUploadForm()
                    shapefile_zip_form.add_error("shapefile_zip", "All .prj, .dbf, .shx, and .shp files must be uploaded.")
                    context = {
                        'shapefile_zip_form': shapefile_zip_form,
                        'image_form': ImageUploadForm(),
                        'video_form': VideoUploadForm(),
                    }
                    return render(request, 'your_template.html', context)
                
                for file in os.listdir(tempdir):
                    file_path = os.path.join(tempdir, file)
                    s3.upload_file(file_path, settings.AWS_STORAGE_BUCKET_NAME, f"shapefiles/{file}")

                return redirect("update_fire_situation", batch_id=batch_id)

    total_count = image_metadata_count + shp_metadata_count + video_metadata_count
    print("Total count of elements:", total_count)

    return render(request, "batch_detail.html", {
        "batch": batch,
        "image_metadata": image_metadata,
        "shp_metadata": shp_metadata,
        "video_metadata": video_metadata,
        "gps_coords": [centroid.y, centroid.x] if centroid else [],
        "zipcode": zipcode,
        "shapefile_zip_form": shapefile_zip_form,
        "image_form": image_form,
        "video_form": video_form,
        "element_type": element_type,
        "total_count": total_count,
        "fire_situation": fire_situation
    })

def update_batch_details(request, batch):
    status = request.POST.get("status")
    tags = request.POST.get("tags")
    if status:
        batch.status = status
    if tags:
        batch.tags = tags
    batch.save()

    update_metadata(request, batch, ImageMetadata, "image_element_")
    update_metadata(request, batch, VideoMetadata, "video_element_")
    update_metadata(request, batch, ShpMetadata, "shp_element_")

def update_metadata(request,batch, model, prefix):
    for obj in model.objects.filter(batch=batch):
        file_name = request.POST.get(f"{prefix}{obj.file_name}")
        if file_name:
            obj.file_name = file_name
            obj.save()
            

def confirm_delete(request, element_name, file_type, batch_id):
    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'yes':
            batch = get_object_or_404(Batch, pk=batch_id)
            model = get_model_for_file_type(file_type)
            handle_file_deletion(element_name, file_type, model, batch)
            return redirect('update_fire_situation', batch_id=batch_id)
        else:
            return redirect('update_fire_situation', batch_id=batch_id)

    context = {
        'element_name': element_name,
        'file_type': file_type,
        'batch_id': batch_id,
    }
    return render(request, 'confirm_delete.html', context)

def get_model_for_file_type(file_type):
    if file_type == "shapefiles":
        return ShpMetadata
    elif file_type == "images":
        return ImageMetadata
    elif file_type == "videos":
        return VideoMetadata
    else:
        raise ValueError("Invalid file type")

def handle_file_deletion(element_name, file_type, model, batch):
    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=f"{file_type}/{element_name}")
    model.objects.filter(batch=batch, file_name=element_name).delete()
    print(f'Deleted {file_type}/{element_name} from {settings.AWS_STORAGE_BUCKET_NAME}')
    

def delete_fire_situation(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id) 
    image_metadata = ImageMetadata.objects.filter(batch=batch)
    image_metadata_count = image_metadata.count()
    shp_metadata = ShpMetadata.objects.filter(batch=batch).first()
    video_metadata = VideoMetadata.objects.filter(batch=batch).first()   
    if request.method == "POST":
        if "delete_batch" in request.POST:  
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            prefixes = ["shapefiles/", "images/", "videos/"]
            
            for prefix in prefixes:
                if shp_metadata and prefix == 'shapefiles/':
                    base_name = shp_metadata.file_name.split('.')[0]
                    extensions = ['.dbf','.prj','.shp', '.shx']
                    for ext in extensions:
                        s3_key = f"{prefix}{base_name}{ext}" 
                        s3.delete_object(Bucket=bucket_name, Key=s3_key)
                        print(f'Deleted {s3_key} from {bucket_name}')
                        
                elif image_metadata_count > 0 and prefix == 'images/':
                    print(image_metadata)
                    for img_data in image_metadata:
                        print(image_metadata)                        
                        s3_key = f"{prefix}{img_data.file_name}"
                        s3.delete_object(Bucket=bucket_name, Key=s3_key)
                        print(f'Deleted {s3_key} from {bucket_name}')
                
                elif video_metadata and prefix == 'videos/':
                    s3_key = f"{prefix}{video_metadata.file_name}"
                    s3.delete_object(Bucket=bucket_name, Key=s3_key)
                    print(f'Deleted {s3_key} from {bucket_name}')
            
            batch.delete()
                
            return redirect('index')    
    return render(request, "confirm_delete.html", {'batch': batch})


def download_files_from_s3(s3, bucket_name, prefix, element_name, batch_name, zip_file, elementType):
    if elementType == "Shapefile":
        base_name = element_name.split('.')[0]
        extensions = ['.dbf','.prj','.shp', '.shx']
        for ext in extensions:
            s3_key = f"{prefix}{base_name}{ext}"
            try:
                file_obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
                zip_file.writestr(f"{batch_name}/{base_name}{ext}", file_obj["Body"].read())
            except s3.exceptions.NoSuchKey:
                print(f"File {s3_key} not found in S3 bucket")
    else:
        s3_key = f"{prefix}{element_name}"
        try:
            file_obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
            zip_file.writestr(f"{batch_name}/{element_name}", file_obj["Body"].read())
        except s3.exceptions.NoSuchKey:
            print(f"File {s3_key} not found in S3 bucket")

def export_data(request):
    element_type = request.POST.get("element_type")
    batch_data_str = request.POST.get("batch_data", "").replace("'", '"')

    try:
        batch_data = json.loads(batch_data_str)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return HttpResponseBadRequest("Invalid batch_data format")
    
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    if element_type == "Shapefile":
        prefix = "shapefiles/"
    elif element_type == "Image":
        prefix = "images/"
    elif element_type == "Video":
        prefix = "videos/"
    else:
        prefix = ["shapefiles/", "images/", "videos/"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for batch in batch_data:
            batch_name = batch.get("batch_name")
            for element in batch.get("elements", []):
                elementType = element.get("element_type")
                element_name = element.get("name")
                
                if element_type is None or element_type == elementType:
                    if isinstance(prefix, list):
                        for prefx in prefix:
                            download_files_from_s3(s3, bucket_name, prefx, element_name, batch_name, zip_file, elementType)
                    else:
                        download_files_from_s3(s3, bucket_name, prefix, element_name, batch_name, zip_file, element_type)

    buffer.seek(0)
    content_disposition = f"attachment; filename={'AllBatches.zip' if element_type is None else f'{element_type}s.zip'}"
    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = content_disposition

    return response 
    
def get_zipcode_from_coordinates(lat, lon):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            for component in data["results"][0]["components"]:
                if "postcode" in data["results"][0]["components"]:
                    return data["results"][0]["components"]["postcode"]
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting postal code: {e}")
        return None
    
@api_view(['GET'])
def batch(request):
    batches = Batch.objects.all()
    serializer = BatchSerializer(batches, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def s3_paths(request, batch_id):
    try:
        images = ImageMetadata.objects.filter(batch_id=batch_id)
        videos = VideoMetadata.objects.filter(batch_id=batch_id)
        image_paths = [img.object_url for img in images]
        video_paths = [vid.object_url for vid in videos]
        return Response({"image_paths": image_paths, "video_paths": video_paths})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_info(request, batch_id):
    try:
        shp_metadata = ShpMetadata.objects.filter(batch_id=batch_id).first()
        if shp_metadata:
            geom = shp_metadata.geom
            centroid = geom.centroid
            response_data = {
                "gps_coordinates": [centroid.y, centroid.x],
                "area": shp_metadata.fire_area,
                "propagation": shp_metadata.fire_propagation,
                "orientation": shp_metadata.fire_orientation
            }
            return Response(response_data)
        else:
            return Response({"error": "No geometry found for batch_id"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_recent_batches(request, batch_id):
    if not batch_id:
        return Response({"error": "batch_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        batch = Batch.objects.filter(id=batch_id).first()
        if not batch:
            return Response({"error": "Batch ID not found"}, status=status.HTTP_404_NOT_FOUND)

        acquisition_date = batch.acquisition_date
        recent_batches = Batch.objects.filter(
            acquisition_date__range=[acquisition_date - timedelta(hours=15), acquisition_date]
        ).exclude(id=batch_id)

        shp_metadata = ShpMetadata.objects.filter(batch_id=batch_id).first()
        if not shp_metadata:
            return Response({"error": "Geometry not found for the given Batch ID"}, status=status.HTTP_404_NOT_FOUND)

        geom = shp_metadata.geom
        intersected_batches = [
            other_batch.id for other_batch in recent_batches
            if ShpMetadata.objects.filter(batch_id=other_batch.id, geom__intersects=geom).exists()
        ]
        intersected_batches.append(batch_id)

        return Response(intersected_batches)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
def change_access_code(request):
    access_code = get_object_or_404(AccessCode, id=1) 
    if request.method == 'POST':
        new_code = request.POST.get('code')
        access_code_form = AccessCodeForm(request.POST, instance=access_code)
        print(new_code)
        print(access_code_form.is_valid())
        if access_code_form.is_valid():
            access_code_form.save()
            return redirect(reverse('index') + '?redirect=mailManagement')
    
    return redirect(reverse('index') + '?redirect=mailManagement')

def add_email(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                EmailList.objects.create(email=email)
                # messages.success(request, 'Email added successfully.')
                return redirect(reverse('index') + '?redirect=mailManagement')
            except Exception as e:
                messages.error(request, f'Error adding email: {e}')
        
        else:
            email_form = EmailForm()
        emails = EmailList.objects.all()
        
    return render(request, 'index.html', {'email_form': email_form,'emails': emails})


def delete_email(request, email_id):
    if request.method == 'POST':
        mailid = get_object_or_404(EmailList, id=email_id)
        mailid.delete()
        return redirect(reverse('index') + '?redirect=mailManagement')