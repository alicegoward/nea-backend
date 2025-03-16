from django.shortcuts import render
from django.core.serializers import serialize
from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from .models import Question
from datetime import datetime

def index(request):
    data = Question.objects.all()
    out = {}
    for i in data:
        out[i.pk] = model_to_dict(i)
    return JsonResponse(out)

def question_detail(request, question_id):
    try:
        question = model_to_dict(Question.objects.get(pk=question_id))
        question["status"] = "success"
        return JsonResponse(question)
    except:
        return JsonResponse({"status":"failure"})

def add_data(request):
    #try:
        data = loads(request.body)
        Question(question_text=data["question_text"], pub_date=timezone.make_aware(datetime.strptime(data["datetime"], '%y-%m-%d-%H-%M-%S'))).save()
        return JsonResponse({"status":"success"})
    #except:
        return JsonResponse({"status":"failure"})