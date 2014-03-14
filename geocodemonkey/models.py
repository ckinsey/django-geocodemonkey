from django.db import models


class GeocodedModel(models.Model):
    """
    This mixin is intended to be dropped on a model for easy storage of geocoder results
    """

    class Meta:
        abstract = True

    # A list of fields that should trigger a re-geocoding
    auto_geocode_on_update = []

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    qualified_address = models.CharField(max_length=256, null=True, blank=True)

    # Functions as a flag for whether or not item has been geocoded.
    # Can also be used to programatically update old geo data
    geocoded = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        self._geocode_concerns = {}
        super(GeocodedModel, self).__init__(*args, **kwargs)
        for concern in self.auto_geocode_on_update:
            # store the original value on init
            self._geocode_concerns[concern] = getattr(self, concern)

    def save(self, *args, **kwargs):
        for concern in self.auto_geocode_on_update:
            if getattr(self, concern) != self._geocode_concerns[concern]:
                self._geocode()

        super(GeocodedModel, self).save(*args, **kwargs)

    def get_geocoding_query(self):
        """
        Generate the address used to geocode an instance of this model.  If only one field is specified in
        auto_geocode_on_update, assumes this field can be used as a standalone query.  If more than one field is
        specified, child classes must override this method to generate a Geocoder compatible
        """
        if len(self.auto_geocode_on_update) == 1:
            return getattr(self, self.auto_geocode_on_update[0])

        raise NotImplementedError("Child classes of GeocodedObjectMixin must implement a get_geocoding_query method"
            " if more than one field is specified in auto_geocode_on_update.")

    def _geocode(self, geocoder=None):
        """
        Reaches out to the default Geocoder and does its thing.
        """
        get_geocoder = __import__('geocodemonkey').get_geocoder
        g = get_geocoder(geocoder)
        g.geocode_to_model_instance(self.get_geocoding_query(), self, commit=False)