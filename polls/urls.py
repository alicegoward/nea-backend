from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("", views.index, name="index"),
    path("detail/<int:question_id>/",views.question_detail, name="question"),
    path("add", views.add_data, name="add_data")
]