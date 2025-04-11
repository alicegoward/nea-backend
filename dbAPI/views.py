from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from .models import Location_data, User, Notification, Route, Path, PathNode
from random import randint
import time
from django.db.models import Q
from django.conf import settings
from dbAPI.graph import GeoPoint
import math

def add_route(request):
    try:
        data = loads(request.body)
        print("some route data", data)
        route = Route(
            user = data["username"],
            end_lat = data["lat"],
            end_long = data["long"],
            end_time = data["endTime"],
            routeName = data["name"]
        )
        route.save()
        print(route)
        for i in data["friends"].values():
            route.participants.add(User.objects.get(username = i))
        return JsonResponse({"success":True})
    except Exception as e:
        print(e)
        return JsonResponse({"success": False, "reason":"unknown error"})
    
def sampleRoute(request):
    data = loads(request.body)
    start_coord = GeoPoint(data["start"]["lat"], data["start"]["long"])
    end_coord = GeoPoint(data["end"]["lat"], data["end"]["long"])
    print(f"coords {start_coord}, {end_coord}")
    a, b = settings.G.closest_pair_from_lat_long(start_coord)
    end = settings.G.closest_from_lat_long(end_coord)
    if ((settings.G.graph[a].position.long-end_coord.long)**2 + (settings.G.graph[a].position.lat-end_coord.lat)**2 < 
        (settings.G.graph[b].position.long-end_coord.long)**2 + (settings.G.graph[b].position.lat-end_coord.lat)**2):
        start = a
    else:
        start = b

    path_db = Path(account = User.objects.get(username = data["user"]))

    print(f"nodes: {start}, {end}")
    route = settings.G.dijkstra(start, (end,))
    node = end
    path = [settings.G.graph[end].position]
    nodes_on_route = []
    while node != a and node != b:
        next_node = route[node].parent
        geometry = list(settings.G.graph[node].neighbours[next_node].geometry)
        if geometry[0] == path[-1]: path+=geometry
        else: path+=geometry[::-1]
        nodes_on_route.append([next_node, route[next_node].dist])
        node = next_node
    if node == a: nodes_on_route+=[[b, settings.G.graph[a].neighbours[b].length]]
    else: nodes_on_route+=[[a, settings.G.graph[b].neighbours[a].length]]
    
    nodes_db = [PathNode(node_id = i[0], path_on = path_db, dist_to_end = i[1]) for i in nodes_on_route]

    path_db.save()
    for i in nodes_db: i.save()


    for i in range(len(nodes_db)-1):
        nodes_db[i].parent_node = nodes_db[i+1]
        nodes_db[i+1].child_node = nodes_db[i]

    for i in nodes_db: i.save()
    path_db.start_node = nodes_db[-1]
    path_db.end_node = nodes_db[0]
    path_db.save()


    print(nodes_on_route)

    data = {}
    for idx, point in enumerate(path):
        data[idx] = {"lat": point.lat, "long": point.long}
    return JsonResponse(data)

def getRoutes(_, user):
    routes = Route.objects.filter(Q(user=user) | Q(participants=user))
    print(routes)
    data = {"success":True, "data":{}}
    for i, route in enumerate(routes):
        route_data = {
            "username": route.user,
            "lat": route.end_lat,
            "long": route.end_long,
            "endTime": route.end_time,
            "name": route.routeName,
            "friends":{}
            }
        for j, friend in enumerate(route.participants.all()):
            route_data["friends"][j] = friend.username
        data["data"][i] = route_data
    return JsonResponse(data)

def location_update(request): 
    data = loads(request.body)
    print("aaaa", data)
    path = Path.objects.filter(account = User.objects.get(username = data["user"]))
    if len(path.all()) == 1: path = path.all()[0]
    else: return JsonResponse(dict())
    if path.current_location != None: path.current_location.delete()
    location = Location_data(datetime=data["datetime"], lat=data["lat"], long=data["long"])
    location.save()
    previous_node = path.start_node
    current_node = previous_node.child_node
    next_node = current_node.child_node
    closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id, GeoPoint(location.lat, location.long))
    while closest_lines_to_node[next_node.node_id] < closest_lines_to_node[previous_node.node_id]:
        print("next section")
        path.start_node = current_node
        previous_node.delete()
        previous_node = current_node
        current_node = next_node
        next_node = current_node.child_node
        closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id, GeoPoint(location.lat, location.long))
    if closest_lines_to_node[previous_node.node_id] > 0.001:
        print("gone off course"+ str(closest_lines_to_node[previous_node.node_id]))
        if path.on_path:
            Notification(notification="gone off course "+str(randint(0,1000)), user=data["user"], datetime=int(time.time())).save()
            path.on_path = False

    geometry_path = [settings.G.graph[current_node.node_id].position]
    while next_node != None:
        next_node
        geometry = list(settings.G.graph[current_node.node_id].neighbours[next_node.node_id].geometry)
        if geometry[0] == geometry_path[-1]: geometry_path+=geometry
        else: geometry_path+=geometry[::-1]
        current_node = next_node
        next_node = current_node.child_node
    geometry_path.insert(0,GeoPoint(location.lat, location.long))
    path.current_location = location
    path.save()
    data = {}
    for idx, point in enumerate(geometry_path):
        data[idx] = {"lat": point.lat, "long": point.long}
    return JsonResponse(data)

def user_info(request):
    try:
        data = loads(request.body)
        user = model_to_dict(User.objects.get(username=data["username"], password=data["password"]))
        print(user)
        user["success"] = True
        user.pop("friends")
        return JsonResponse(user)
    except:
        return JsonResponse({"success":False, "reason":"username / password combination does not exist"})

def add_user(request):
    try:
        data = loads(request.body)
        if User.objects.filter(username = data["username"]).count() > 0:
            raise Exception
        print("aaaa", data)
        User(username=data["username"], password=data["password"]).save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"user already taken"})
    
def create_notification(_, user):
    try:
        Notification(notification="some sample text "+str(randint(0,1000)), user=user, datetime=int(time.time())).save()
        return JsonResponse({"success":True})
    except Exception as e:
        print(e)
        return JsonResponse({"success":False})
    
def deactivate(_, user):
    Path.objects.filter(account = User.objects.get(username=user)).delete()
    return JsonResponse({'success':True})

def show_notification(_, user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime]=i.notification
    Notification.objects.all().delete()
    return JsonResponse({"success": True, "notifications": data})

def get_friends(_, user):
    try:
        user = User.objects.get(username=user)
        friend_data = {}
        for i, friend in enumerate(user.friends.all()):
            friend_data[i] = friend.username
        incoming_data = {}
        for i, friend in enumerate(user.pending_friends.all()):
            incoming_data[i] = friend.username
        outgoing_data = {}
        for i, friend in enumerate(User.objects.filter(pending_friends=user)):
            outgoing_data[i] = friend.username
        print(f"{friend_data}\n{incoming_data}\n{outgoing_data}")
        return JsonResponse({"success": True, "names":friend_data, "incoming":incoming_data, "outgoing":outgoing_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason":str(e)})
    
def add_friend(request):
    try:
        data = loads(request.body)
        requesting = User.objects.get(username=data["userRequesting"])
        requested = User.objects.get(username=data["userRequested"])
        requested.pending_friends.add(requesting)
        Notification(
            user = requested, 
            notification = f"{requesting} has requested to add you as a friend.", 
            datetime = int(time.time())
            ).save()
        requesting.save()
        return JsonResponse({"success":True, "reason":"user successfully added"})
    except:
        return JsonResponse({"success": False, "reason":"user does not exist"})
    
def update_friend_state(request):
    data = loads(request.body)
    accepting = User.objects.get(username=data["userAccepting"])
    accepted = User.objects.get(username=data["userAccepted"])
    accepting.pending_friends.remove(accepted)
    if data["result"] == "accepted":
        accepting.friends.add(accepted)
    accepting.save()
