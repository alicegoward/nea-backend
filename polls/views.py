from django.shortcuts import render
from django.core.serializers import serialize
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from .models import Question

def index(request):
    data = Question.objects.all()
    data = [model_to_dict(i) for i in Question.objects.all()]
    return JsonResponse(data, safe=False)

def question_detail(request, question_id):
    question = Question.objects.get(pk=question_id)
    return JsonResponse(model_to_dict(question))

def add_data(request):
    question_text = request.GET.get('text')
    Question(question_text=question_text, pub_date=timezone.now()).save()
    return JsonResponse({"status":"success"})