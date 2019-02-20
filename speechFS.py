import boto3
from django.core.files.storage import default_storage
from speech.models import AudioClip
import subprocess
from shutil import move
import datetime
from decouple import config
import os
from tempfile import NamedTemporaryFile,gettempdir
from django.core.files import File
from django import db

#this file has the methods resposible of the file system

#save file as a db-model instance
def saveFile(_file,_guid):
    
    temp_audio = NamedTemporaryFile(suffix='.wav',delete=False)
    temp_audio.close()
    recompileAudioFile(_file,temp_audio.name)
    wav_guid = rename_filename_post_conversion(_guid)
    ac = AudioClip(file_clip=File(open(temp_audio.name,"rb")),guid=wav_guid,lang='Undecided',was_correct=True)
    ac.file_clip.name = wav_guid
    ac.save()
    os.unlink(temp_audio.name)


#simple get from AC objects with specific guid
def get_ac_instance(_guid):
    ac = AudioClip.objects.filter(guid=_guid).first()
    return ac

#convert audiofile for normalization
def recompileAudioFile(_file,tmpname):
    tmp_file_path = _file.temporary_file_path()
    ffmpeg_command = 'ffmpeg -y -i '+  tmp_file_path + ' -acodec pcm_u8 -ar 16000 ' + tmpname
    subprocess.call(ffmpeg_command, shell=True)

def get_correct_percent():
    correct = AudioClip.objects.filter(was_correct=True).count()
    wrong = AudioClip.objects.filter(was_correct=False).count() 

    if(correct == 0):
        correct = 1
    db.reset_queries()


    return round((100*correct / (correct + wrong)),2)

#debugging only, not used in production
def download_files():
    heb_files = AudioClip.objects.filter(lang="Hebrew")
    eng_files = AudioClip.objects.filter(lang="English")
    print(heb_files.count())
    print(eng_files.count())

    s3 = boto3.resource('s3', aws_access_key_id=config('AWS_ACCESS_KEY_ID') , aws_secret_access_key= config('AWS_SECRET_ACCESS_KEY'))
    bucket = s3.Bucket('audioml-bucket')

    for file in eng_files:
        _object = bucket.Object('media/'+ file.guid)
        print(file.guid)
        _object.download_file("E/"+file.guid)


#simple string conversion - post audio conversion
def rename_filename_post_conversion(_string):
        return _string.replace("ogg","wav")