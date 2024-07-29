# In models.py

from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point


class Batch(models.Model):
    batch_name = models.CharField(max_length=100)
    tags = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    acquisition_date = models.DateField()
    
    class Meta:
        db_table = 'batch'  

    def __str__(self):
        return self.batch_name

class ShpMetadata(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=100)
    fire_area = models.CharField(max_length=100)
    fire_propagation = models.CharField(max_length=100)
    fire_orientation = models.CharField(max_length=100)
    # geom = gis_models.GeometryField(srid=4326, default=Point(0, 0))
    geom = gis_models.GeometryField(srid=4326)
    
    class Meta:
        db_table = 'shp_metadata'  

class ImageMetadata(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=100)
    object_url = models.URLField()
    
    class Meta:
        db_table = 'image_metadata'  

class VideoMetadata(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=100)
    object_url = models.URLField()
    
    class Meta:
        db_table = 'video_metadata'  
        
class AccessCode(models.Model):
    code = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.code

class EmailList(models.Model):
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email

