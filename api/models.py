from datetime import datetime

from django.db import models
from django.utils.crypto import get_random_string


class LocationData(models.Model):
    """
    Most recent location data from a user's path along a route.
    Previous values not stored as it is unnecessary and would take up a large amount of storage.
    """
    lat = models.FloatField()
    long = models.FloatField()
    datetime = models.BigIntegerField()


class User(models.Model):
    """
    Data about each user.
    Friends and pending_friends are both many to many fields, Django automatically creates a link table.
    """
    username = models.CharField(max_length=200, primary_key=True)
    password = models.CharField(max_length=200)
    friends = models.ManyToManyField("self", symmetrical=True)
    pending_friends = models.ManyToManyField("self", symmetrical=False)
    token = models.CharField(max_length=16, default=get_random_string(16))

    def __str__(self) -> str:
        return self.username


class Waypoint(models.Model):
    """
    Django generates a primary key (id) by default and this is the only required feature of a Waypoint
    """
    pass


class PathNode(models.Model):
    """
    Per node (street junction) on a route
    Parent and child nodes are the previous and next nodes, so deleting one implies the entire path is deleted.
    "dist_waiting_at_node" is the time spent waiting for other people if the node is a waypoint, converted into meters
    at a normal walking speed as all calculations are done in meters.
    """
    node_id = models.BigIntegerField()
    parent_node = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    child_node = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    path_on = models.ForeignKey('Path', on_delete=models.CASCADE)
    dist_to_end = models.FloatField()
    dist_waiting_at_node = models.FloatField(default=0)
    waypoint = models.ForeignKey(Waypoint, on_delete=models.SET_NULL, null=True)


class Path(models.Model):
    """
    Unlike the route, this is the actual track that a person is taking, so only exists if they have activated the route.
    Offset from start is the distance ahead of the first node that the user is, as therefore the edge that they are on
    is still defined.
    """
    start_node = models.ForeignKey(PathNode, on_delete=models.SET_NULL, null=True, related_name='+')
    end_node = models.ForeignKey(PathNode, on_delete=models.SET_NULL, null=True, related_name='+')
    account = models.ForeignKey(User, on_delete=models.CASCADE)
    current_location = models.ForeignKey(LocationData, on_delete=models.SET_NULL, null=True, related_name='+')
    on_path = models.BooleanField(default=True)
    offset_from_start = models.FloatField(null=True)
    related_route = models.ForeignKey('Route', on_delete=models.CASCADE, related_name='+', null=True)
    eta = models.DateTimeField(default=datetime.now())


class UserOnRoute(models.Model):
    """
    This is another many-to-many relationship, but is manually defined due to configuration settings being specific for
    each user on a route.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    route = models.ForeignKey('Route', on_delete=models.CASCADE)
    create_mor = models.BooleanField(default=True)
    mor_tolerance_s = models.FloatField(default=300)
    reroute_tolerance_m = models.FloatField(default=50)
    auto_notify_late = models.FloatField(default=600)


class Route(models.Model):
    """
    This is the overall route settings. The __str__ method is for debugging only.
    """
    routeName = models.CharField(max_length=200)
    user = models.CharField(max_length=200)
    end_lat = models.FloatField()
    end_long = models.FloatField()
    end_time = models.BigIntegerField()
    junction_name = models.CharField(max_length=1000)

    def __str__(self) -> str:
        return "route" + str(self.end_lat) + self.user + str(self.end_long)


class Notification(models.Model):
    """
    These are stored and timestamped until the relevant client requests notifications.
    """
    user = models.CharField(max_length=200)
    notification = models.CharField(max_length=1000)
    datetime = models.IntegerField()
