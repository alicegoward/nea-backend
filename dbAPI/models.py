from django.db import models


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")
    def __str__(self):
        return self.question_text
    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Location_data(models.Model):
    user = models.CharField(max_length=200)
    lat = models.FloatField()
    long = models.FloatField()
    datetime = models.IntegerField()

class User(models.Model):
    username = models.CharField(max_length=200, primary_key=True)
