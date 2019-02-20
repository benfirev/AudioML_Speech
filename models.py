from django.db import models

# Create your models here.

class AudioClip(models.Model):
    file_clip = models.FileField() #Audio file
    lang = models.TextField()       #string of the language ("Hebrew","English")
    guid = models.TextField()       #guid and filename for identification
    uploaded_at = models.DateTimeField(auto_now_add=True) 
    was_correct = models.BooleanField() #was guessed correctly for later statistics
    def __str__(self):
        return (self.lang + " - " + str(self.was_correct))

class ModelWeights(models.Model):
    file_weights = models.FileField() #keras saved model (.npy numpy format)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_ready = models.BooleanField(default=False) #final is_ready boolean to ensure the weights aren't loaded befor fully built

    def __str__(self):
        return str(self.uploaded_at)