from django.core.cache import cache

from easy_maps.geocode import google_v3

import requests
import re
import logging


class BaseGeocoder(object):
    """
    Handles the basic geocoder features like cache managment and returning
    normalized data structures.

    Geocoder implementations must specify the _geocode method which does the
    backend specific geocoding effort.
    """

    def __init__(self):
        self.qualified_address = ""
        self.lat = None
        self.long = None

    def _generate_cache_key(self, address):
        """Normalizes addresses for more effective caching"""
        return re.sub(r'[^a-z0-9]', '', address.lower())

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

    def _geocode(self):
        raise NotImplementedError


class GoogleGeocoder(BaseGeocoder):

    def _geocode(self, address):
        qa, lat_long = google_v3(address)
        return qa, lat_long


class GeocoderUSGeocoder(BaseGeocoder):

    def _geocode(self, address):
        r = requests.get("http://rpc.geocoder.us/service/csv?address=%s" % (address))
        if r.status_code == 200:
            segments = r.text.split(',')
            qa = ", ".join(segments[2:])
            return qa, (segments[0], segments[1])
