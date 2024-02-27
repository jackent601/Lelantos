from django.contrib.gis import forms

# Mainly for widgeting map
class LocationEntryForm(forms.Form):
    location = forms.PointField(widget=forms.OSMWidget(
                    attrs={
                            'default_lat': 54.5966,
                            'default_lon': -5.9301,
                            'default_zoom': 9,
                            }))