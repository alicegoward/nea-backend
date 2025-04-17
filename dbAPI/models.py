from django.db import models

class Location_data(models.Model):
    lat = models.FloatField()
    long = models.FloatField()
    datetime = models.BigIntegerField()

class User(models.Model):
    username = models.CharField(max_length=200, primary_key=True)
    password = models.CharField(max_length=200)
    friends = models.ManyToManyField("self", symmetrical=True)
    pending_friends = models.ManyToManyField("self", symmetrical=False)

    def __str__(self):
        return self.username

class Waypoint(models.Model):
    pass

class PathNode(models.Model):
    node_id = models.BigIntegerField()
    parent_node = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    child_node = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    path_on = models.ForeignKey('Path', on_delete=models.CASCADE)
    dist_to_end = models.FloatField()
    dist_waiting_at_node = models.FloatField(default = 0)
    waypoint = models.ForeignKey(Waypoint, on_delete=models.SET_NULL, null=True)
    
class Path(models.Model):
    start_node = models.ForeignKey(PathNode, on_delete=models.SET_NULL, null=True, related_name='+')
    end_node = models.ForeignKey(PathNode, on_delete=models.SET_NULL, null=True, related_name='+')
    account = models.ForeignKey(User, on_delete=models.CASCADE)
    current_location = models.ForeignKey(Location_data, on_delete=models.SET_NULL, null=True, related_name='+')
    on_path = models.BooleanField(default=True)
    offset_from_start = models.FloatField(null=True)
    related_route = models.ForeignKey('Route', on_delete=models.CASCADE, related_name='+', null=True)
    
class Route(models.Model):
    routeName = models.CharField(max_length=200)
    user = models.CharField(max_length=200)
    end_lat = models.FloatField()
    end_long = models.FloatField()
    end_time = models.BigIntegerField()
    participants = models.ManyToManyField("user")

    def __str__(self):
        return "route"+str(self.end_lat)+self.user+str(self.end_long)


class Notification(models.Model):
    user = models.CharField(max_length=200)
    notification = models.CharField(max_length=1000)
    datetime = models.IntegerField()