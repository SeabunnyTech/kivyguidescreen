from kivy.properties import ObjectProperty, AliasProperty


class GuideScreenVariableProperty(AliasProperty):

    def __init__(self, varname, **kw):
        super().__init__(self._get_object, self._set_varname, **kw)
        self._varname = varname

    def _get_object(self, *args):
        print(*args)
        return self

    def read(self):
        varname = self._varname
        var = self.manager.settings[varname]
        if isinstance(var, dict):
            var = QueryDict(var)
        return var

    def _set_varname(self, caller, value):
        if not isinstance(value, str):
            raise "GuideScreenVariableProperty must be set to a variabel name, not {}".format(type(value))
        self._varname = value

    def write(self, value):
        self.manager.settings[self._varname] = value

   