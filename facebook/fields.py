import logging
logger = logging.getLogger(__name__)

from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import simplejson as json
from django.conf import settings

if 'south' in settings.INSTALLED_APPS:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^facebook\.fields\.JSONField"])


class JSONFormField(forms.fields.CharField):
    def clean(self, value, *args, **kwargs):
        if value == '{}': # let empty value pass.
            pass
        elif value:
            try:
                # Run the value through JSON so we can normalize formatting and at least learn about malformed data:
                value = json.dumps(json.loads(value), cls=DjangoJSONEncoder)
            except ValueError:
                raise forms.ValidationError("Invalid JSON data!")

        return super(JSONFormField, self).clean(value, *args, **kwargs)


class JSONField(models.TextField):
    """
    TextField which transparently serializes/unserializes JSON objects

    See:
    http://www.djangosnippets.org/snippets/1478/
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    formfield = JSONFormField

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if isinstance(value, dict) or isinstance(value, list):
            return value
        elif isinstance(value, basestring):
            # Avoid asking the JSON decoder to handle empty values:
            if not value:
                return {}

            try:
                return json.loads(value)
            except ValueError:
                logging.exception("Unable to deserialize store JSONField data: %s", value)
                return {}
        else:
            assert value is None
            return {}

    def get_prep_value(self, value):
        """Convert our JSON object to a string before we save"""
        return self._flatten_value(value)

    def value_to_string(self, obj):
        """Extract our value from the passed object and return it in string form"""

        if hasattr(obj, self.attname):
            value = getattr(obj, self.attname)
        else:
            assert isinstance(obj, dict)
            value = obj.get(self.attname, "")

        return self._flatten_value(value)

    def _flatten_value(self, value):
        """Return either a string, JSON-encoding dict()s as necessary"""
        if not value:
            return ""

        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        assert isinstance(value, basestring)

        return value