from django.db import models

class GeocodedObjectMixin(object):
    """
    This mixin is intended to be dropped on a model for easy storage of geocoder results
    """

    # A list of fields that should trigger a re-geocoding
    auto_geocode_on_update = []

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    qualified_address = models.CharField(max_length=256)

    # Functions as a flag for whether or not item has been geocoded.
    # Can also be used to programatically update old geo data
    geocoded = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        self._geocode_concerns = {}
        super(GeocodedObjectMixin, self).__init__(*args, **kwargs)
        for concern in self.auto_geocode_on_update:
            # store the original value on init
            self._geocode_concerns[concern] = getattr(self, concern)

    def save(self, *args, **kwargs):
        for concern in self.auto_geocode_on_update:
            if getattr(self, concern) != self._geocode_concerns[concern]:
                self._geocode()

        super(GeocodedObjectMixin, self).save(*args, **kwargs)

    def _geocode(self):
        """
        Reaches out to the default Geocoder and does its thing.
        """
        get_geocoder = __import__('geocodemonkey').get_geocoder
        g = get_geocoder()
        g.geocode_to_model_instance(self.get_geocoding_address, self, commit=False)