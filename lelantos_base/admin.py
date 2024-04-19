from django.contrib import admin

# from django.contrib.gis.admin import OSMGeoAdmin

from .models import Session, Wp3_Authentication_Token, User_Action, Location

admin.site.register(Session)
admin.site.register(Wp3_Authentication_Token)
admin.site.register(User_Action)

admin.site.register(Location)

# @admin.register(Location)
# class LocationAdmin(OSMGeoAdmin):
#     list_display = ('name', 'city', 'location')


