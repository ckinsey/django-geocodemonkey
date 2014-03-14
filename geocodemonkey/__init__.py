import re
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str
from django.utils.timezone import now
from geopy import geocoders as geopy_geocoders
from geopy.exc import GeocoderServiceError

from models import GeocodedModel as geo_model


def get_geocoder(geocoder=None):
    """
    Returns a GeocodeMonkeyGeooder instance linked to the specificed backend.  If no backend is provided, returns the
    an instance tied to the backend referenced by the GEOCODERS['default'] setting
    """

    if geocoder is None:
        geocoder = 'default'

    if settings.GEOCODERS.get(geocoder, False):
        return GeocodeMonkeyGeocoder(settings.GEOCODERS[geocoder])
    else:
        raise ImproperlyConfigured(
            "Could not find geocoder config for '%s'.  If no identifier was specified, please define a valid default geocoder in the "
            "GEOCODERS setting" % geocoder)


class GeocodeMonkeyGeocoder(object):
    """
    Handles the basic geocoder features like cache management and returning
    normalized data structures.
    """

    def __init__(self, *args, **kwargs):
        # Sets the class to be used for geocoding.  args[0] should be dict from the GEOCODERS setting
        self.geocoder_class = getattr(geopy_geocoders, args[0]['BACKEND'])

        # Set whether or not this is an asynchronous geocoder
        self.ASYNC = args[0].get('ASYNC', False)

        self.qualified_address = ""
        self.lat = None
        self.long = None

    def _generate_cache_key(self, address):
        """
        Normalizes addresses for more effective caching
        """

        return re.sub(r'[^a-z0-9]', '', str(address).lower())

    def store_geocoded_address(self, qa, lat, long):
        self.qualified_address = qa
        self.lat = lat
        self.long = long

    def geocode(self, address):
        # check the cache first
        key = self._generate_cache_key(address)
        cached_geocode = cache.get(key)
        if cached_geocode:
            self.store_geocoded_address(cached_geocode[0], cached_geocode[1], cached_geocode[2])
            logging.debug("Address %s geocoded from cache with key %s" % (address, key))
        else:
            qa, lat_long = self._geocode(address)
            cache.set(key, (qa, lat_long[0], lat_long[1]), None)
            self.store_geocoded_address(qa, lat_long[0], lat_long[1])
            logging.debug("Address %s geocoded from web API and stored with key %s" % (address, key))

        if self.lat and self.long:
            return self.qualified_address, (self.lat, self.long)
        else:
            raise LookupError("Geocoder %s did not return an address for %s" % (self.__class__, address))

    def geocode_to_model_instance(self, address, instance, commit=True):
        """
        Performs a geocoding and saves it to the instance that was passed in.
        It is expected that the instance inhertis from geocodemonkey.models.GeocodedObjectMixin
        """
        if not isinstance(instance, geo_model):
            raise TypeError("Instance argument is expected to be derived from geocodemonkey.models.GeocodedModel base class")

        # If this is an async Geocoder, we want to perform this asynchronously
        if self.ASYNC:
            from celery.app import Celery
            # Always commit on async
            celery = Celery()
            return celery.task(args=[self._geocode_to_model_instance(address, instance, commit=True)])
        else:
            return self._geocode_to_model_instance(address, instance, commit=commit)

    def _geocode_to_model_instance(self, address, instance, commit):
        qa, lat_long = self.geocode(address)
        instance.qualified_address = qa
        instance.latitude = lat_long[0]
        instance.longitude = lat_long[1]
        instance.geocoded = now()

        if commit:
            instance.save()

        return instance

    def _geocode(self, address):
        """
        Instantiates the geopy Geocoder and nabs an address
        """
        try:
            g = self.geocoder_class()
            address = smart_str(address)
            return g.geocode(address, exactly_one=False)[0]
        except (UnboundLocalError, ValueError, GeocoderServiceError) as e:
            raise Exception(e)