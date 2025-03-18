from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("", views.index, name="index"),
    path("add_location", views.location_update, name="add_location"),
    path("user/view/<str:user>/", views.user_info, name="user"),
    path("user/add", views.add_user, name="user")
]   