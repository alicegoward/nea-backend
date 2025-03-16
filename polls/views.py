from django.shortcuts import render
from django.core.serializers import serialize
from django.forms.models import model_to_dict
from django.http import JsonResponse
from .models import Question

def index(request):
    data = Question.objects.all()
    data = [model_to_dict(i) for i in data]
    return JsonResponse(data, safe=False)