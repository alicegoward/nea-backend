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
    pending_friends = models.ManyToManyField("self", symmetrical=False)

    def __str__(self):
        return self.username
    
class Route(models.Model):
    user = models.CharField(max_length=200)
    end_lat = models.FloatField()
    end_long = models.FloatField()
    end_time = models.IntegerField()
    participants = models.ManyToManyField("user")

    def __str__(self):
        return "route"+str(self.end_lat)+self.user+str(self.end_long)

class Notification(models.Model):
    user = models.CharField(max_length=200)
    notification = models.CharField(max_length=1000)
    datetime = models.IntegerField()