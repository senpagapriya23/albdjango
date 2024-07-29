from rest_framework import serializers
from .models import Batch, ShpMetadata, ImageMetadata, VideoMetadata

class BatchSerializer(serializers.ModelSerializer):
    acquisition_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    class Meta:
        model = Batch
        fields = ['id', 'acquisition_date']

class ShpMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShpMetadata
        fields = ['geom', 'fire_area', 'fire_propagation', 'fire_orientation']

class ImageMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageMetadata
        fields = ['object_url']

class VideoMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoMetadata
        fields = ['object_url']
