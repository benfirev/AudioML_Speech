from django.contrib import admin
from .models import AudioClip, ModelWeights

# Register your models here.
admin.site.register(AudioClip)
admin.site.register(ModelWeights)
