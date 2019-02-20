from django.shortcuts import render,redirect
from django.http import Http404,HttpResponse,JsonResponse
from django.core.files.storage import FileSystemStorage
from speech.speechML import detect_from_file,decice_if_train
from speech.speechFS import saveFile
import uuid
import os
from django.conf import settings
from speech.speechFS import get_ac_instance,get_correct_percent,rename_filename_post_conversion

def index(request):
    return render(request,"speech/home.html")


def record(request):
    if(request.method == "POST"):
        if("audio_blob" in request.FILES):
            # if you get a POST request with a file (the audio recording)
            audio_binary = request.FILES["audio_blob"]
            file_name = audio_binary.name
            saveFile(audio_binary,audio_binary.name)
            detection = detect_from_file(rename_filename_post_conversion(file_name))
            return HttpResponse(detection)

        if("correct" in request.POST):
            #if you get a POST request with var "correct" - after predicition

            is_correct_bool = (request.POST["correct"] == "True") 
            pred_lang = (request.POST["detection"] == "Hebrew")
            correct_lang = not (pred_lang ^ is_correct_bool) # True => Hebrew; Flase => English  
            _lang = "English"
            if(correct_lang):
                _lang = "Hebrew"
            ac = get_ac_instance(rename_filename_post_conversion(request.POST["audio_guid"]))
            ac.lang = _lang
            ac.was_correct = is_correct_bool
            ac.save()
            decice_if_train()
            
    return render(request,"speech/record.html",{"audio_guid":uuid.uuid4()})
    

def endscreen(request,correct):
    correct_percent = get_correct_percent()
    return render(request,"speech/endscreen.html",{"correct":correct,"c_p":correct_percent})

