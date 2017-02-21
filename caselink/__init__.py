import os
from abc import ABCMeta, abstractproperty
from ConfigParser import SafeConfigParser

import requests


PKGDIR = os.path.dirname(__file__)
CONFIG = DEFAULT = {
    "caselink-url": "http://127.0.0.1:8888/",
    "timeout": "30",
    "debug": "off"
}


CONFIG_SECTION = "server"
# Config loading priority:
CURDIR_CONFIG = ".caselink-python.cfg"
LOCAL_CONFIG = os.path.expanduser("~") + "/.caselink-python.cfg"
GLOBAL_CONFIG = "/etc/caselink-python.cfg"
PKG_CONFIG = "%s/caselink-python.cfg" % PKGDIR


def _load_config():
    config = SafeConfigParser(DEFAULT)
    if not config.read([PKG_CONFIG, GLOBAL_CONFIG, LOCAL_CONFIG, CURDIR_CONFIG]) or \
            not config.has_section(CONFIG_SECTION):
        raise RuntimeError("Config files not avaliable")

    CONFIG.update(
        dict(
            [(k, config.get(CONFIG_SECTION, k)) for k in CONFIG.keys()]
        )
    )

_load_config()
CASELINK_URL = CONFIG['caselink-url']


def lazy_property(fn):
    lazy_name = '__lazy__' + fn.__name__
    @property
    def lazy_eval(self):
        if not hasattr(self, lazy_name):
            setattr(self, lazy_name, fn(self))
        return getattr(self, lazy_name)
    return lazy_eval


class CaseLinkItem():
    """
    Base Class for all Caselink Item
    """
    __metaclass__ = ABCMeta
    base_url = None

    @abstractproperty
    def url(self):
        pass

    @abstractproperty
    def id(self):
        pass

    @property
    def json(self):
        if hasattr(self, '__caselink__json'):
            return getattr(self, '__caselink__json')
        else:
            if self.exists():
                return getattr(self, '__caselink__json')
            else:
                setattr(self, '__caselink__json', {})
                return getattr(self, '__caselink__json')

    @json.setter
    def json(self, value):
        setattr(self, '__caselink__json', value)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError('No atrribute: ' + str(name))
        if not name in self.json:
            raise AttributeError('No atrribute: ' + str(name))
        return self.json[name]

    @classmethod
    def create(cls, **kwargs):
        res = requests.post(cls.base_url, json=kwargs)
        res.raise_for_status()

        return cls(res.json()['id'])

    def refresh(self):
        """
        Refetch info from caselink, remove all cached properties.
        """
        respons = requests.get(self.url)
        #Raise error if anything went wrong.
        respons.raise_for_status()
        self.json = respons.json()
        for attr, value in self.__dict__.iteritems():
            if attr.startswith('__lazy__'):
                delattr(self, attr)
        return self

    def exists(self):
        if hasattr(self, '__caselink__json'):
            return True
        try:
            self.refresh()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            else:
                raise e
        return True

    def save(self):
        if self.exists():
            requests.put(self.url, self.json)
        else:
            if hasattr(self, '__caselink__json'):
                requests.post(self.url, json=self.json)
        self.refresh()

    def delete(self):
        if self.exists():
            requests.delete(self.url)
        else:
            raise RuntimeError()

    # Following functions consider caselink stay the same during
    # the life circle of a CaseLinkItem object.
    def __eq__(self, other):
        if not isinstance(other, CaseLinkItem):
            return False
        return self.url == other.url

    def __lt__(self, other):
        return self.url < other.url

    def __hash__(self):
        return self.url

    def __str__(self):
        return "<CaselinkItem " + str(self.id) + ">"

    def __repr__(self):
        return self.__str__()


class AutoCase(CaseLinkItem):
    base_url = CASELINK_URL + 'autocase/'
    def __init__(self, case_id):
        self._id = str(case_id)
        self._url = self.base_url + str(case_id) + '/'

    def __str__(self):
        return "<AutoCase " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def linkages(self):
        return [Linkage(link) for link in self.json['linkages']]

    @linkages.setter
    def linkages_setter(self, _):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def workitems(self):
        return [WorkItem(link.workitem) for link in self.linkages]

    @workitems.setter
    def workitems_setter(self, _):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def bugs(self):
        return [Bug(bug) for bug in self.json['bugs']]

    @bugs.setter
    def bugs_setter(self, _):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")

    @lazy_property
    def autocase_failures(self):
        return [AutoCaseFailure(failure) for failure in self.json['autocase_failures']]

    @autocase_failures.setter
    def autocase_failures_setter(self, _):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")


class WorkItem(CaseLinkItem):
    base_url = CASELINK_URL + 'workitem/'
    def __init__(self, case_id):
        self._id = str(case_id)
        self._url = self.base_url + str(case_id) + '/'

    def __str__(self):
        return "<WorkItem " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def linkages(self):
        return [Linkage(link) for link in self.json['linkages']]

    @linkages.setter
    def linkages_setter(self, _):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def autocases(self):
        cases = []
        for link in [Linkage(link_id) for link_id in self.json['linkages']]:
            cases.extend(link.autocases)
        return cases

    @autocases.setter
    def autocases_setter(self):
        raise RuntimeError("Please Use create()")

    @lazy_property
    def bugs(self):
        return [Bug(bug) for bug in self.json['bugs']]


class Bug(CaseLinkItem):
    base_url = CASELINK_URL + 'bug/'
    def __init__(self, bz_id):
        self._id = str(bz_id)
        self._url = self.base_url + str(bz_id) + '/'

    def __str__(self):
        return "<Bug " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

class AutoCaseFailure(CaseLinkItem):
    unique_together = ("failure_regex", "autocase_pattern",)
    base_url = CASELINK_URL + 'autocase_failure/'

    def __init__(self, id):
        """
        Failures uses a surrogate key
        """
        self._id = str(id)
        self._url = self.base_url + str(id) + '/'

    def __str__(self):
        return "<Failure " + str(self.id) + ">"

    @classmethod
    def create(cls, failure_regex, autocase_pattern, **kwarg):
        kwarg.update({
            'failure_regex': failure_regex,
            'autocase_pattern': autocase_pattern,
        })
        return super(AutoCaseFailure, cls).create(**kwarg)

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def bug(self):
        return Bug(self.json['bug'])

    @lazy_property
    def autocases(self):
        return [AutoCase(case) for case in self.json['autocases']]

    @lazy_property
    def blacklist_entries(self):
        return [BlackListEntry(bl) for bl in self.json['blacklist_entries']]

    @autocases.setter
    def autocase_setter(self, autocases):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")


class Linkage(CaseLinkItem):
    unique_together = ("workitem", "autocase_pattern",)
    base_url = CASELINK_URL + 'linkage/'

    def __init__(self, id):
        """
        Linkage uses a surrogate key
        """
        self._id = str(id)
        self._url = self.base_url + str(id) + '/'

    def __str__(self):
        return "<Linkage workitem:" + str(self.workitem) + " pattern: " + str(self.autocase_pattern) + ">"

    @classmethod
    def create(cls, workitem, autocase_pattern, **kwarg):
        kwarg.update({
            'workitem': workitem,
            'autocase_pattern': autocase_pattern,
        })
        return super(Linkage, cls).create(**kwarg)

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def autocases(self):
        return [AutoCase(case) for case in self.json['autocases']]

    @autocases.setter
    def autocase_setter(self, autocases):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")


class BlackListEntry(CaseLinkItem):
    base_url = CASELINK_URL + 'blacklist/'

    def __init__(self, id):
        """
        Surrogate key
        """
        self._id = str(id)
        self._url = self.base_url + str(id) + '/'

    def __str__(self):
        return "<BlackListEntry:" + str(self.status) + ", id: " + str(self.id) + ">"

    @classmethod
    def create(cls, status, workitems, autocase_failures, **kwarg):
        kwarg.update({
            'status': status,
            'workitems': workitems,
            'autocase_failure': autocase_failures,
        })
        return super(BlackListEntry, cls).create(**kwarg)

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def autocase_failures(self):
        return [AutoCaseFailure(failure) for failure in self.json['autocase_failures']]

    @lazy_property
    def workitems(self):
        return [WorkItem(wi) for wi in self.json['workitems']]

    @workitems.setter
    def workitems_setter(self, value):
        self.json['workitems'] = value

    @lazy_property
    def autocases(self):
        cases = []
        for failure in [AutoCaseFailure(failure) for failure in self.json['autocase_failures']]:
            for autocase in failure.autocases:
                cases.append(AutoCase(autocase))
        return cases

    @autocases.setter
    def autocases_setter(self):
        raise RuntimeError("Please Use create()")
