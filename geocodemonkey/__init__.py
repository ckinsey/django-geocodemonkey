from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import geocoders

def get_geocoder(klass=None):
    """
    Returns the geocodemonkey GeoCoder class provided in the klass string.  If no klass is provided, returns the
    class referenced by the DEFAULT_GEOCODER setting
    """

    try:
        module = __import__('geocodemonkey')
        print module
        if klass is None:
            klass = settings.DEFAULT_GEOCODER
        g_klass = getattr(module.geocoders, klass)
        return g_klass
    except AttributeError:
        raise ImproperlyConfigured(
            "Could not find geocoder class %s.  If no class was specified, please define a valid geocoder class in the "
            "DEFAULT_GEOCODER setting" % klass)
