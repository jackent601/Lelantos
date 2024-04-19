from django.contrib.gis import forms
from lelantos.settings import DEFAULT_LOCATION_SETTINGS   

# # Mainly for widgeting map
class LocationEntryForm(forms.Form):
    location = forms.PointField(
        widget=forms.OSMWidget(
                    attrs={
                            'default_lat': DEFAULT_LOCATION_SETTINGS['default_lat'],
                            'default_lon': DEFAULT_LOCATION_SETTINGS['default_lon'],
                            'default_zoom': 9,
                            'display_raw':True,
                            }))