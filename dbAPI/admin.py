from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(PathNode)
admin.site.register(Path)
admin.site.register(Route)
admin.site.register(Notification)
admin.site.register(Location_data)
admin.site.register(Waypoint)