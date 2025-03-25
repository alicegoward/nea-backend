from django.db import models

class Location_data(models.Model):
    user = models.CharField(max_length=200)
    lat = models.FloatField()
    long = models.FloatField()
    datetime = models.IntegerField()

class User(models.Model):
    username = models.CharField(max_length=200, primary_key=True)
    password = models.CharField(max_length=200)
    friends = models.ManyToManyField("self", symmetrical=True)

    def __str__(self):
        return self.username

class Notification(models.Model):
    user = models.CharField(max_length=200)
    notification = models.CharField(max_length=1000)
    datetime = models.IntegerField()