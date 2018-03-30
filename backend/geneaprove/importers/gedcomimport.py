"""
Provides a gedcom importer
"""

from django.utils.translation import ugettext as _
import django.utils.timezone
from geneaprove.utils.gedcom import Gedcom, Invalid_Gedcom, \
        GedcomRecord, GedcomString
from geneaprove import models
from django.db import transaction, connection
import geneaprove.importers
import re
import datetime
import logging
import traceback
import time
import os

logger = logging.getLogger('geneaprove.importers')

# If true, the given name read from gedcom is split (on spaces) into
# a given name and one or more middle names. This might not be appropriate
# for all languages.
GIVEN_NAME_TO_MIDDLE_NAME = True

# If true, a different persona is created for each source. For instance,
# if person ID001 has two events (birth and death) each with its own sources,
# then two personas (or more) will be created for ID001, all joined through
# a "sameAs" persona-to-persona relationship.
MULTIPLE_PERSONAS = True

DEBUG = False

# Id used for inlined sources in gedcom (ie there is no id in the gedcom
# file)
INLINE_SOURCE = -2
NO_SOURCE = -1

FORM_TO_MIME = {
    'jpeg': 'image/jpeg',  # Gramps
    'image/png': 'image/png',  # Gramps
    'image/jpeg': 'image/jpeg',
    'png': 'image/png',  # rootsMagic
    'jpg': 'image/jpg',  # rootsMagic
    'JPG': 'image/jpg',  # rootsMagic
    '': 'application/octet-stream'}


def as_list(obj):
    """
    Encapsulate obj in a list, if it is not a list already.
    """
    if not obj:
        return []
    elif isinstance(obj, list):
        return obj
    else:
        return [obj]


def location(obj):
    """Return the location (in the gedcom file) of obj"""

    try:
        return as_list(obj)[0].location()
    except AttributeError:
        return "???"


def parse_gedcom_date(data_date):
    """
    Return a datetime object from data (a DATE record).
    The TIME is also taken into account, if specified.
    """
    if data_date:
        date = data_date.value
        if data_date.TIME:
            tmp = datetime.datetime.strptime(
                date + " " + data_date.TIME, "%d %b %Y %H:%M:%S")
        else:
            tmp = datetime.datetime.strptime(date, "%d %b %Y")

        return django.utils.timezone.make_aware(
            tmp, django.utils.timezone.get_default_timezone())

    return None


##################################
# Sources manager
##################################

class SourceManager(object):
    """
    A class responsible for creating sources in the database, from sources
    and source references in Gedcom.
    The goal is that all sources in Gedcom are created in the database (even
    if they have no associated asserts). On the other hand, we want to merge
    a source and its reference when there is only one of the latter.
    This avoids lots of useless sources in the database.
    """

    def __init__(self, importer, gedcom_name, whole_file):
        """
        :param GedcomImporter importer:
        :param GedcomRecord whole_file: the whole gedcom file, used to check
           which sources have references and how many of those.
        """
        self.importer = importer
        self.sources = {}  # sourceId => models.Source
        self.refs = {}    # sourceId => [GedcomRecord] for refs to that source

        gedcom_date = parse_gedcom_date(whole_file.HEAD.DATE)
        self.__source_for_gedcom = models.Source.objects.create(
            higher_source_id=None,
            subject_place=None,
            jurisdiction_place_id=None,
            researcher=self.importer._researcher,
            subject_date=str(gedcom_date),
            medium="",
            title=gedcom_name,
            abbrev=gedcom_name,
            biblio=gedcom_name,
            last_change=gedcom_date,
            comments='')

        # Count the number of references for each source
        for key, value, level in whole_file.for_all_fields_recursive(level=1):
            if key == "SOUR" and level > 1 and isinstance(value, GedcomRecord):
                self.refs.setdefault(value.value, []).append(value)

    def add_SOUR(self, source, subject_place=None):
        """
        :param GedcomRecord source: a SOUR record from gedcom
        :return: A models.Source object
        """
        return self.__create_source(source, subject_place=subject_place)

    def __add_OBJE_to_source(self, source, obje):
        """
        Create object representations in the database
        :param models.Source source: the source to which we add a
           representation
        :param GedcomRecord obje: the OBJE description. This can also be a
           list of such objects
        """
        for o in as_list(obje):
            if o is None:
                continue
            if isinstance(o, str):
                self.importer.report_error('Ignore OBJE reference: %s' % o)
                continue

            obj = self.importer._objects.get(o.FILE, None)
            if not obj or obj.comments != o.TITL:
                mime = FORM_TO_MIME.get(o.FORM, 'application/octet-stream')
                self.importer._objects[o.FILE] = models.Representation.objects.create(
                    source=source, mime_type=mime, file=o.FILE,
                    comments=o.TITL)

    def __add_source_to_REPO(self, source, repo):
        """
        Add a source to a repository
        :param models.Source source: the source to which we add a
           representation
        :param GedcomRecord repo: the REPO description.
        """

        if repo:
            # If we just have a "CALN", no need to create a repository
            rep = self.importer._create_repo(repo)
            caln = None   # Description of the call number
            source_type = None

            for k, v in repo.for_all_fields():
                if k == "CALN":
                    if len(v) > 1:
                        self.importer.report_error(
                            "%s A single CALN per REPO is supported" % (
                                location(v), ))
                    else:
                        caln = v[0].value
                        source_type = (v[0].MEDI or '').lower()
                else:
                    self.importer.report_error(
                        "%s Unhandled REPO.%s" % (location(v), k))

            models.Repository_Source.objects.create(
                repository=rep,
                source=source,
                # activity=None,
                call_number=caln,
                description=source_type)

    def __create_source(self, sour, subject_place=None):
        """
        Actual creation in the database
        :param GedcomRecord sour: a SOUR record from gedcom
        :param subject_place: the place the source is about
        :return: A models.Source object
        """
        title = getattr(sour, "TITL", "Unnamed source")

        src = models.Source.objects.create(
            higher_source=self.__source_for_gedcom,
            subject_place=subject_place,
            jurisdiction_place_id=None,
            researcher=self.importer._researcher,
            subject_date=None,
            medium="",
            title=title,
            abbrev=getattr(sour, "ABBR", "") or title,
            biblio=title,
            last_change=self.importer._create_CHAN(
                getattr(sour, "CHAN", None)),
            comments='')

        self.__add_OBJE_to_source(src, sour.OBJE)
        self.__add_source_to_REPO(src, getattr(sour, "REPO", None))

        for k, v in sour.for_all_fields():
            if k == "id":
                # ??? Should we preserve gedcom ids ?
                pass

            elif k not in ("REPO", "OBJE", "TITL", "CHAN", "ABBR"):
                self.importer.report_error(
                    "%s Unhandled SOUR.%s" % (location(v), k))

        if hasattr(sour, "id"):
            self.sources[sour.id] = src

        return src

    def create_sources_ref(self, data):
        """
        Create a list of instances of Source for the record described by
        DATA. For instance, if Data is an event, these are all the sources in
        which the event was references.

        :return: [(source_id, models.Source)] or [None]
        """

        if not isinstance(data, str) and getattr(data, "SOUR", None):
            all_sources = []

            for s in data.SOUR:

                # Whether to add new parts to the source we found, rather than
                # create a child source (this is true for sources defined
                # inline or sources with a single xref)

                extend_source = False

                # As a convenience for the python API (this doesn't happen in a
                # Gedcom file), we allow direct source creation here. In
                # Gedcom, this is always an xref.

                if not s.value or s.value not in self.sources:
                    sour = (INLINE_SOURCE, self.__create_source(s))
                    extend_source = True
                else:
                    sour = (s.value, self.sources[s.value])
                    extend_source = len(self.refs[s.value]) <= 1

                # If we have parts, we possibly need to create a nested source

                parts = []
                for k, v in s.for_all_fields():
                    if k == "DATA":
                        for k2, v2 in v.for_all_fields():
                            parts.append((k2, v2))
                    elif k in ("NOTE", "OBJE"):
                        pass   # Handled separately below
                    else:
                        parts.append((k, v))

                parts_string = u"".join(u" %s=%s" % p for p in parts)

                if parts:
                    # Try to reuse an existing source with the same parts,
                    # since gedcom duplicates them
                    new_id = '%s %s' % (s.value, parts_string)
                    if new_id in self.sources:
                        nested_source = self.sources[new_id]
                    else:
                        if extend_source:
                            nested_source = sour[1]  # The parent source
                        else:
                            nested_source = models.Source.objects.create(
                                higher_source=sour[1],
                                researcher=self.importer._researcher,
                                title=(sour[1].title or u'') + parts_string,
                                abbrev=(sour[1].abbrev or u'') + parts_string,
                                comments="",
                                last_change=sour[1].last_change)
                            self.sources[new_id] = nested_source
                            nested_source.comments += self.importer._get_note(
                                s)
                            nested_source.save()

                        for k, v in parts:
                            typ = self.importer._citation_part_types.get(k, None)
                            if typ is None:
                                typ = models.Citation_Part_Type.objects.create(
                                    name=k.title(), gedcom=k)
                                self.importer._citation_part_types[k] = typ

                            self.importer._all_citation_parts.append(
                                models.Citation_Part(
                                    type=typ, value=v, source=nested_source))

                    self.__add_OBJE_to_source(
                        nested_source, getattr(s, "OBJE", None))

                    sour = (sour[0], nested_source)

                all_sources.append(sour)

            return all_sources

        return [(NO_SOURCE, self.__source_for_gedcom)]


##################################
# GedcomImporter
##################################


class GedcomImporter(object):

    """
    Abstract Gedcom importer. This translates from the gedcom data model
    into our own, and can be used by any importer for which the software
    uses roughly the gedcom model.
    """

    def __init__(self, gedcom_name, data):
        """
        From the data contained in a gedcom-like file (see description of
        the format in gedcom.py), creates corresponding data in the database.
        data is an instance of GedcomData.
        """

        if DEBUG:
            logger.info("Start import")

        self._data = data
        self._researcher = self._create_researcher()
        prj = self._create_project(self._researcher)

        self._default_surety = list(prj.scheme.parts.all())
        self._default_surety = \
            self._default_surety[int(len(self._default_surety) / 2)]

        self._births = dict()  # Index on gedcom persona id, contains Event

        self._objects = dict()  # Objects that were inserted in this import
        # to avoid duplicates.  file => Representation

        self._obje_for_places = dict()
        # The OBJE created for each place.
        # This is needed because at least GRAMPS outputs the PLAC for an
        # event along with all its OBJE (so we have lots of duplicates)

        self._principal = models.Event_Type_Role.objects.get(
            pk=models.Event_Type_Role.PK_principal)
        self._birth__father = models.Event_Type_Role.objects.get(
            pk=models.Event_Type_Role.PK_birth__father)
        self._birth__mother = models.Event_Type_Role.objects.get(
            pk=models.Event_Type_Role.PK_birth__mother)

        self._event_types = dict()
        self._char_types = dict()
        self._citation_part_types = dict()
        self._place_part_types = dict()
        self._places = dict()
        self._repo = dict()
        self._p2p_types = dict()

        self._create_enum_cache()

        self._all_place_parts = []    # list of Place_Part to bulk_create
        self._all_p2c = []            # list of P2C to bulk_create
        self._all_p2e = []            # list of P2E to bulk_create
        self._all_p2p = []            # list of P2P to bulk_create
        self._all_char_parts = []     # list of Characteristic_Part
        self._all_citation_parts = [] # list of Citation_Part

        self._sourcePersona = dict()  # Indexed on (sourceId, gedcom personId)
        # returns the Persona to use for that source. As a special
        # case, sourceId is set to NO_SOURCE for those events and
        # characteristics with no source.

        self.source_manager = SourceManager(self, gedcom_name, data)

        for r in data.REPO:
            self._create_repo(r)
        if DEBUG:
            logger.info("Done importing repositories")

        for s in data.SOUR:
            self.source_manager.add_SOUR(s)

        for index, s in enumerate(data.INDI):
            self._create_bare_indi(s)

        max = len(data.INDI)
        if DEBUG:
            logger.info("Importing %d indi" % max)
        for index, s in enumerate(data.INDI):
            self._create_indi(s)
            if DEBUG and index % 20 == 0:
                logger.info("%d / %d (%0.2f %%)" % (
                    index, max, float(index) / float(max) * 100.0))
        if DEBUG:
            logger.info("Done importing indi")

        if DEBUG:
            logger.info("Importing %d families" % (len(data.FAM)))
        for s in data.FAM:
            self._create_family(s)
        if DEBUG:
            logger.info("Done importing families")

        models.Place_Part.objects.bulk_create(self._all_place_parts)
        models.P2C.objects.bulk_create(self._all_p2c)
        models.P2E.objects.bulk_create(self._all_p2e)
        models.P2P.objects.bulk_create(self._all_p2p)
        models.Characteristic_Part.objects.bulk_create(self._all_char_parts)
        models.Citation_Part.objects.bulk_create(self._all_citation_parts)

        for k, v in data.for_all_fields():
            if k not in ("SOUR", "INDI", "FAM", "HEAD", "SUBM",
                         "TRLR", "ids", "filename"):
                self.report_error(
                    "%s Unhandled FILE.%s" % (location(v), k))

    def report_error(self, msg):
        logger.info(msg)

    def _create_enum_cache(self):
        """Create a local cache for enumeration tables"""

        for evt in models.Event_Type.objects.exclude(gedcom__isnull=True):
            if evt.gedcom:
                self._event_types[evt.gedcom] = evt

        types = models.Characteristic_Part_Type.objects.exclude(
            gedcom__isnull=True)
        for c in types:
            if c.gedcom:
                self._char_types[c.gedcom] = c

        self._char_types['_MIDL'] = \
            models.Characteristic_Part_Type.objects.get(gedcom='_MIDL')
        # Handled specially in _create_characteristic
        self._char_types['NAME'] = True

        for p in models.Place_Part_Type.objects.exclude(gedcom__isnull=True):
            if p.gedcom:
                self._place_part_types[p.gedcom] = p

        cit_part_types = models.Citation_Part_Type.objects.exclude(
            gedcom__isnull=True)
        for p in cit_part_types:
            self._citation_part_types[p.gedcom] = p

        for p in models.P2P_Type.objects.all():
            self._p2p_types[p.name.lower()] = p

    def _create_CHAN(self, data):
        """data should be a form of CHAN"""

        # In Geneatique 2010, there can be several occurrences of CHAN. But
        # we only preserve the most recent one

        result = None
        for d in as_list(data):
            tmp = parse_gedcom_date(d.DATE)
            if result is None or (tmp is not None and tmp > result):
                result = tmp

        if result:
            return result
        else:
            return django.utils.timezone.now()

    def _create_repo(self, data):
        """
        Create a repository, or return an existing one.
        """

        if data.value and self._repo.get(data.value, None):
            return self._repo[data.value]

        info = []
        if getattr(data, "WWW", None):
            info.append("\nURL=".join(data.WWW))
        if getattr(data, "PHON", None):
            info.append("\nPhone=".join(data.PHON))
        if getattr(data, "RIN", None):
            info.append("\nRIN=" + data.RIN)
        if getattr(data, "NOTE", None):
            info.append(self._get_note(data))

        info = "".join(info)
        r = None
        addr = getattr(data, "ADDR", None)
        name = getattr(data, "NAME", "")

        if info or addr or name:
            r = models.Repository.objects.create(
                place=None,
                addr=addr,
                name=name or info,
                type=None,
                info=info)

            if data.id:
                self._repo[data.id] = r

        for k, v in data.for_all_fields():
            # CALN is handled directly in the source itself
            if k not in ("NAME", "ADDR", "WWW", "PHON", "RIN", "NOTE", "id",
                         "CALN"):
                self.report_error("%s Unhandled REPO.%s" % (location(v), k))

        return r

    def _create_family(self, data):
        """Create the equivalent of a FAMILY in the database"""

        husb = data.HUSB
        if husb:
            husb = self._sourcePersona[(NO_SOURCE, husb.id)]

        wife = data.WIFE
        if wife:
            wife = self._sourcePersona[(NO_SOURCE, wife.id)]

        family_events = ("MARR", "DIV", "CENS", "ENGA", "EVEN")
        found = 0

        # We might have a family with children only.
        # Or a family with only one parent.
        # In such cases, we create the missing parents, so the the siblings
        # are not lost (if we created a single parent, their might still
        # be ambiguities if that parent also belonged to another family

        if not husb:
            husb = models.Persona.objects.create(name="@Unknown@")
        if not wife:
            wife = models.Persona.objects.create(name="@Unknown@")

        for field in family_events:
            for evt in getattr(data, field, []):
                found += 1
                self._create_event(
                    [(husb, self._principal), (wife, self._principal)],
                    field, evt, CHAN=data.CHAN)

        # if there is no event to "build" the family, we generate a dummy
        # one. Otherwise there would be no relationship between husband and
        # wife in the geneaprove database, thus losing information from gedcom

        if found == 0:
            family_built = GedcomRecord()
            family_built.setLine(data._line)
            self._create_event(
                [(husb, self._principal), (wife, self._principal)],
                "MARR",
                family_built,
                CHAN=data.CHAN)

        # Now add the children.
        # If there is an explicit BIRT event for the child, this was already
        # fully handled in _create_indi, so we do nothing more here. But if
        # there is no known BIRT even, we still need to associate the child
        # with its parents.

        for c in data.CHIL:
            # Associate parents with the child's birth event. This does not
            # recreate an event if one already exists.

            if self._births.get(c.id, None) is None:
                self._create_event(
                    indi=[
                        (self._sourcePersona[(
                            NO_SOURCE, c.id)], self._principal),
                        (husb, self._birth__father),
                        (wife, self._birth__mother)],
                    field="BIRT", data=c, CHAN=data.CHAN)

        for k, v in data.for_all_fields():
            if k not in ("CHIL", "HUSB", "WIFE", "id",
                         "CHAN") + family_events:
                self.report_error("%s Unhandled FAM.%s" % (location(v), k))

    def _addr_image(self, data):
        result = ""
        if data:
            for (key, val) in data.for_all_fields():
                result += ' %s=%s' % (key, val)
        return result

    def _internal_create_place(self, data, addr):
        """
        Check if the place already exists, since GEDCOM will duplicate
        places unfortunately.
        We need to take into account all the place parts, which is done
        by simulating a long name including all the optional parts.

        Take into account all parts (the GEDCOM standard only defines a
        few of these for a PLAC, but software such a gramps add quite a
        number of fields

        :param data: the parent node ("ADDR")
           This node might include a "MAP" child for latitude/longitude
        :param addr: the actual address node ("PLAC" or "ADR1")
        """

        map = getattr(data, "MAP", None)

        lookup_name = data.value + self._addr_image(addr)
        if map:
            lookup_name += ' MAP=%s,%s' % (map.LATI, map.LONG)

        p = self._places.get(lookup_name)
        if not p:
            # ??? Should create hierarchy of places
            p = models.Place.objects.create(
                name=data.value,
                date=None,
                parent_place=None)

            self._places[lookup_name] = p  # For reuse

            if map:
                self._all_place_parts.append(models.Place_Part(
                    place=p,
                    type=self._place_part_types['MAP'],
                    name=map.LATI + ' ' + map.LONG))

            if addr:
                for key, val in addr.for_all_fields():
                    if key != 'value' and val:
                        part = self._place_part_types.get(key, None)
                        if not part:
                            self.report_error(
                                'Unknown place part: ' + key)
                        else:
                            self._all_place_parts.append(models.Place_Part(
                                place=p, type=part, name=val))

        # ??? Unhandled attributes of PLAC: FORM, SOURCE and NOTE
        # FORM would in fact tell us how to split the name to get its
        # various components, which we could use to initialize the place
        # parts

        for k, v in data.for_all_fields():
            if k not in ("MAP", ):
                self.report_error(
                    "%s Unhandled PLAC.%s" % (location(v), k))

        return p

    def _create_place(self, data, id=''):
        """If data contains a subnode PLAC, parse and returns it.
        """

        if data is None:
            return None

        addr = getattr(data, "ADDR", None)
        plac = getattr(data, "PLAC", None)

        if addr is None and plac is None:
            return None

        # We have a "ADDR", but no "PLAC": in Gramps, this corresponds to
        # filling the "Address" information for a person. This should get
        # converted to a RESI event, and we'll create a place for it. We
        # seem to have more info in the ADR1 subfield
        if plac is None and addr is not None:
            return self._internal_create_place(addr, addr)

        return self._internal_create_place(plac, addr)

    def _indi_for_source(self, sourceId, indi):
        """Return the instance of Persona to use for the given source.
           A new one is created as needed.
           sourceId should be "INLINE_SOURCE" for inline sources (since this
           source cannot occur in a different place anyway).
           sourceId should be "NO_SOURCE" when not talking about a specific
           source.
        """

        if not MULTIPLE_PERSONAS \
           or sourceId == NO_SOURCE \
           or not hasattr(indi, "_gedcom_id"):
            return indi

        if sourceId != INLINE_SOURCE:
            p = self._sourcePersona.get((sourceId, indi._gedcom_id), None)
            if p:
                return p

        ind = models.Persona.objects.create(
            name=indi.name,
            description='',  # was set for the first persona already
            last_change=indi.last_change)

        if sourceId != INLINE_SOURCE:
            self._sourcePersona[(sourceId, indi._gedcom_id)] = ind

        # Link old and new personas

        self._all_p2p.append(
            models.P2P(
                surety=self._default_surety,
                researcher=self._researcher,
                person1=indi,
                person2=ind,
                type_id=models.P2P_Type.sameAs,
                rationale='Single individual in the gedcom file'))

        return ind

    def _get_note(self, data):
        """Retrieves the NOTE information from data, if any. Such notes can
           be xref, which are automatically resolved here.
        """
        n = []
        for p in getattr(data, "NOTE", []):
            if p.startswith("@") and p.endswith("@"):
                n.append(self._data.obj_from_id(p).value)
            else:
                n.append(p)

        return "\n\n".join(n)

    def _create_characteristic(self, key, value, indi):
        """Create a Characteristic for the person indi.
         Return True if a characteristic could be created, false otherwise.
         (key,value) come from the GEDCOM structure.

         A call to this subprogram might look like:
            self._create_characteristic(
                key="NAME",
                value=GedcomRecord(SURN=g.group(2), GIVN=g.group(1)),
                indi=indi)

            self._create_characteristic("SEX", "Male", indi)

         As defined in the GEDCOM standard, and except for the NAME which
         is special, all other attributes follow the following grammar:
             n TITL nobility_type_title
             +1 <EVENT_DETAIL>
         where EVENT_DETAIL can define any of the following: TYPE, DATE,
         PLAC, ADDR, AGE, AGNC, CAUS, SOUR, NOTE, MULT
        """

        if key == 'NAME':
            # Special handling for name: its value was used to create the
            # person itself, and now we are only looking into its subelements
            # for the components of the name
            typ = None
        else:
            typ = self._char_types[key]

        value = as_list(value)

        for val_index, val in enumerate(value):
            if val is None:
                continue

            # Create the Characteristic object iself.
            # This also computes its place and date.

            if isinstance(val, GedcomString):
                c = models.Characteristic.objects.create(
                    place=None,
                    name=(typ and typ.name) or key.capitalize())
                str_value = val
            else:
                # Processes ADDR and PLAC
                place = self._create_place(val)
                self._create_obje_for_place(val, place)  # processes OBJE

                c = models.Characteristic.objects.create(
                    place=place,
                    name=(typ and typ.name) or key.capitalize(),
                    date=getattr(val, "DATE", None))
                str_value = val.value

            # Associate the characteristic with the persona.
            # Such an association is done via assertions, based on sources.

            self._all_p2c.extend(
                models.P2C(
                    surety=self._default_surety,
                    researcher=self._researcher,
                    person=self._indi_for_source(sourceId=sid, indi=indi),
                    source=s,
                    characteristic=c)
                for sid, s in self.source_manager.create_sources_ref(val)
            )

            # The main characteristic part is the value found on the same
            # GEDCOM line as the characteristic itself. For simple
            # characteristics like "SEX", this will in fact be the only part.

            if typ:
                self._all_char_parts.append(
                    models.Characteristic_Part(
                        characteristic=c, type=typ, name=str_value))

            # We might have other characteristic part, most notably for names.

            if isinstance(val, GedcomRecord):
                midl = self._char_types['_MIDL']

                for k, v in val.for_all_fields():
                    t = self._char_types.get(k, None)
                    if t:
                        if k == 'NOTE':
                            # This will be automatically added as a
                            # characteristic part because initialdata.txt
                            # defines this. However, in gedcom these notes can
                            # be xref, so resolve them here.

                            n = self._get_note(val)
                            if n:
                                self._all_char_parts.append(
                                    models.Characteristic_Part(
                                        characteristic=c, type=t, name=n))

                        elif k == 'GIVN' and GIVEN_NAME_TO_MIDDLE_NAME:
                            if v:
                                n = v.replace(',', ' ').split(' ')
                                self._all_char_parts.append(
                                    models.Characteristic_Part(
                                        characteristic=c, type=t, name=n[0]))
                                self._all_char_parts.extend(
                                    models.Characteristic_Part(
                                        characteristic=c, type=midl, name=m)
                                    for m in n[1:] if m
                                )

                        elif v:
                            self._all_char_parts.append(
                                models.Characteristic_Part(
                                    characteristic=c, type=t, name=v))

                    elif k == 'SOUR':
                        pass  # handled in the create_sources_ref loop above

                    elif k in ("ADDR", "PLAC", "OBJE"):
                        pass  # handled in _create_place

                    elif k == "DATE":
                        pass  # handled above

                    elif k == "TYPE" and key == "NAME":
                        pass  # handled

                    else:
                        self.report_error("%s Unhandled %s.%s" % (
                            location(val), key, k))

    def _create_obje_for_place(self, data, place, CHAN=None):
        # If an event has an OBJE: since the source is an xref, the object
        # is in fact associated with the place. Unfortunately, it will be
        # duplicated among all other occurrences of that place (which itself
        # is duplicated).

        if getattr(data, "OBJE", None):
            # Make sure we do not add the same OBJE multiple times for a
            # given place, and in addition create a source every time
            known_obje = self._obje_for_places.setdefault(place, set())
            obje = [ob
                    for ob in getattr(data, "OBJE", None)
                    if getattr(ob, "TITL", "") not in known_obje]
            known_obje.update(getattr(ob, "TITL", "") for ob in obje)

            if obje:
                if getattr(data, "PLAC", None) and place:
                    self.source_manager.add_SOUR(
                        GedcomRecord(
                            REPO=None,
                            CHAN=CHAN,
                            TITL='Media for %s' % data.PLAC.value,
                            OBJE=obje),
                        subject_place=place)
                else:
                    self.report_error("%s Unhandled OBJE" %
                                      (location(data.OBJE)))

    def _create_event(self, indi, field, data, CHAN=None):
        """Create a new event, associated with INDI by way of one or more
           assertions based on sources.
           INDI is a list of (persona, role). If persona is None, it will be
           ignored.
           It can be a single persona, in which case the role is "principal".
           For a BIRT event, no new event is created if one already exists for
           the principal. There must be a single principal for a BIRT event.
        """

        evt_name = ""

        # This is how Gramps represents events entered as
        # a person's event (ie partner is not known)

        if field == 'EVEN':
            if data.TYPE == 'Marriage':
                event_type = self._event_types['MARR']
            elif data.TYPE == 'Engagement':
                event_type = self._event_types['ENGA']
            elif data.TYPE == 'Residence':
                event_type = self._event_types['RESI']
            elif data.TYPE == 'Separation':
                event_type = self._event_types['DIV']  # ??? incorrect
            elif data.TYPE == 'Military':
                event_type = self._event_types['_MIL']
            elif data.TYPE == 'Unknown':
                event_type = self._event_types['EVEN']
            else:
                evt_name = "%s " % data.TYPE
                event_type = self._event_types['EVEN']
        else:
            event_type = self._event_types[field]

        # Find the principal for this event

        if isinstance(indi, list):
            principal = None
            name = []

            for (k, v) in indi:
                if k and v == self._principal:
                    name.append(k.name)
                    principal = k

            name = " and ".join(name)

            if principal is None:
                self.report_error(
                    "%s No principal given for event: %s - %s" % (
                        location(data), field, data))

        else:
            principal = indi
            name = principal.name
            indi = [(indi, self._principal)]

        evt = None

        # Can we find a descriptive name for this event ?

        if event_type.gedcom == 'BIRT':
            name = 'Birth of ' + name
            evt = self._births.get(principal._gedcom_id, None)
        elif event_type.gedcom == 'MARR':
            name = 'Marriage of ' + name
        elif event_type.gedcom == "DEAT":
            name = "Death of " + name
        else:
            name = "%s of %s" % (evt_name or event_type.name, name)

        # Create the event if needed.

        if not evt:
            place = self._create_place(data)
            self._create_obje_for_place(data, place, CHAN)  # processes OBJE
            evt = models.Event.objects.create(
                type=event_type, place=place,
                name=name, date=getattr(data, "DATE", None))

            if event_type.gedcom == 'BIRT':
                self._births[principal._gedcom_id] = evt
            all_src = self.source_manager.create_sources_ref(data)
        else:
            all_src = self.source_manager.create_sources_ref(None)

        last_change = self._create_CHAN(CHAN)

        for person, role in indi:
            if person:
                n = ""
                if role == self._principal:
                    # If we have a note associated with the event, we assume it
                    # deals with the event itself, not with its sources.  Since
                    # the note also appears in the context of an INDI, we store
                    # it in the assertion.

                    n = self._get_note(data)

                self._all_p2e.extend(
                    models.P2E(
                        surety=self._default_surety,
                        researcher=self._researcher,
                        person=self._indi_for_source(sourceId=sid, indi=person),
                        event=evt,
                        source=s,
                        role=role,
                        last_change=last_change,
                        rationale=n)
                    for sid, s in all_src
                )

        for k, v in data.for_all_fields():
            # ADDR and PLAC are handled in create_place
            # SOURCE is handled in create_sources_ref
            if k not in ("DATE", "ADDR", "PLAC", "SOUR", "TYPE", "OBJE",
                         "NOTE", "_all", "xref"):
                self.report_error("%s Unhandled EVENT.%s" % (location(v), k))

        return evt

    def _create_bare_indi(self, data):
        """
        Create an entry for an INDI in the database, with no associated event
        or characteristic.
        """
        if not data.NAME:
            name = ''
        else:
            name = data.NAME[0].value  # Use first available name

        # The name to use is the first one in the list of names
        indi = models.Persona.objects.create(
            name=name,
            description=self._get_note(data.NOTE),
            last_change=self._create_CHAN(data.CHAN))
        indi._gedcom_id = data.id
        self._sourcePersona[(NO_SOURCE, data.id)] = indi

    def _create_indi(self, data):
        """Add events and characteristics to an INDI"""

        indi = self._sourcePersona[(NO_SOURCE, data.id)]

        # For all properties of the individual

        for field, value in data.for_all_fields():
            if field == "id":
                # ??? Should we preserve the GEDCOM @ID001@
                pass

            elif field in ("FAMC", "FAMS"):
                # These are ignored: families are created through marriage or
                # child births.
                pass

            elif field in ("CHAN", "NOTE"):
                # Already handled
                pass

            elif field == "BIRT":
                # Special case for births, since we need to associate the
                # parents as well (so that they share the same source)
                local_indi = [(indi, self._principal)]
                for famc in as_list(data.FAMC):
                    if famc.HUSB:
                        local_indi.append(
                            (self._sourcePersona[(NO_SOURCE, famc.HUSB.id)],
                             self._birth__father))
                    if famc.WIFE:
                        local_indi.append(
                            (self._sourcePersona[(NO_SOURCE, famc.WIFE.id)],
                             self._birth__mother))

                for v in value:
                    self._create_event(
                        indi=local_indi, field=field, data=v, CHAN=data.CHAN)

            elif field in self._char_types:
                self._create_characteristic(field, value, indi)

            elif field in self._event_types:
                for v in value:
                    self._create_event(
                        indi=indi, field=field, data=v, CHAN=data.CHAN)

            elif field.startswith("_") and \
                    (isinstance(value, str) or
                     (isinstance(value, list) and
                      isinstance(value[0], str))):
                # A GEDCOM extension by an application.  If this is a simple
                # string value, assume this is a characteristic.  Create the
                # corresponding type in the database, and import the field

                if field not in self._char_types:
                    self._char_types[field] = \
                        models.Characteristic_Part_Type.objects.create(
                            is_name_part=False,
                            name=field,
                            gedcom=field)

                for v in as_list(value):
                    self._create_characteristic(field, v, indi)

            elif field == "SOUR":
                # The individual is apparently cited in a source, but is not
                # related to a specific GEDCOM event. So instead we associate
                # with a general census event.
                evt_data = GedcomRecord(SOUR=value)
                self._create_event(indi, field="CENS", data=evt_data)

            elif field == "OBJE":
                self._create_characteristic(
                    key="_IMG",
                    value=GedcomRecord(
                        value='',
                        SOUR=[GedcomRecord(
                            TITL="Media for %s" % indi.name,
                            CHAN=None,
                            OBJE=value)]),
                    indi=indi)

            elif field == "ASSO":
                # There can be one or more ASSO, so we receive a list
                assert isinstance(value, list)   # of GedcomRecord

                for val in value:
                    related = self._sourcePersona[(NO_SOURCE, val.value)]
                    relation = None

                    for f, v in val.for_all_fields():
                        if f == "RELA":
                            relation = self._p2p_types.get(v.lower(), None)
                            if relation is None:
                                relation = models.P2P_Type.objects.create(name=v)
                                self._p2p_types[v.lower()] = relation

                        else:
                            self.report_error("%s Unhandled INDI.ASSO.%s" % (
                                location(value), f))

                    if relation is not None:
                        self._all_p2p.append(
                            models.P2P(
                                surety=self._default_surety,
                                researcher=self._researcher,
                                person1=indi,
                                person2=related,
                                type=relation))

            else:
                self.report_error("%s Unhandled INDI.%s" % (
                    location(value), field))

        return indi

    def _create_project(self, researcher):
        """Register the project in the database"""

        filename = getattr(self._data.HEAD, "FILE", "") or \
            self._data.get_filename()
        p = models.Project.objects.create(
            name='Gedcom import',
            description='Import from ' +
            filename,
            scheme=models.Surety_Scheme.objects.get(id=1))
        models.Researcher_Project.objects.create(
            researcher=researcher,
            project=p,
            role='Generated GEDCOM file')
        return p

    @staticmethod
    def _addr_to_string(data):
        """
      Convert an ADDR field to a single string. Our model does use different
      fields for current addresses
        """

        if data:
            addr = data.value + '\n'
            if data.ADR1:
                addr += data.ADR1 + '\n'
            if data.ADR2:
                addr += data.ADR2 + '\n'
            if data.POST:
                addr += data.POST + '\n'
            if data.CITY:
                addr += data.CITY + '\n'
            if data.STAE:
                addr += data.STAE + '\n'
            if data.CTRY:
                addr += data.CTRY + '\n'

            # Gramps sets this when the address is not provided
            addr = addr.replace('Not Provided', '')

            # Cleanup empty lines
            return re.sub('^\n+', '', re.sub('\n+', '\n', addr))
        else:

            return ''

    def _create_researcher(self):
        """
      Create the Researcher that created the data contained in the gedcom
      file
        """

        subm = self._data.HEAD.SUBM
        if subm:
            return models.Researcher.objects.create(
                name=subm.NAME.value or 'unknown',
                comment=GedcomImporter._addr_to_string(subm.ADDR))
        else:
            return models.Researcher.objects.create(name='unknown', comment='')

##################################
# GedcomImporterCumulate
##################################


class GedcomImporterCumulate(GedcomImporter):

    def __init__(self, gedcom_name, data, *args, **kwargs):
        self.errors = []
        super().__init__(
            *args, gedcom_name=gedcom_name, data=data, **kwargs)

    def report_error(self, msg):
        self.errors.append(msg)


##################################
# GedcomFileImporter
##################################

class GedcomFileImporter(geneaprove.importers.Importer):
    """Register a new importer in geneaprove: imports GEDCOM files"""

    class Meta:
        """see inherited documentation"""
        displayName = _('GEDCOM')
        description = _(
            'Imports a standard GEDCOM file, which most genealogy' +
            ' software can export to')

    def __init__(self):
        self._parser = None  # The gedcom parser
        super().__init__()

    def parse(self, filename):
        """Parse and import a gedcom file.
           :param filename:
               Either the name of a file, or an instance of a class compatible
               with file().
           :return:
               A tuple (success, errors), where errors might be None
        """

        try:
            logger.info('Start parsing %s' % filename)
            parsed = Gedcom().parse(filename)
            logger.info('Done parsing %s' % filename)

            if isinstance(filename, str):
                name = filename
            elif hasattr(filename, 'name'):
                name = filename.name
            else:
                name = 'uploaded'

            gedcom_name = (
                'GEDCOM "%s", %s, exported from %s,' +
                ' created on %s, imported on %s') % (
                    os.path.basename(name),
                    parsed.HEAD.SUBM.NAME.value if parsed.HEAD.SUBM else 'unknown',
                    parsed.HEAD.SOUR.value,
                    parse_gedcom_date(parsed.HEAD.DATE).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"),
                    datetime.datetime.now(
                        django.utils.timezone.get_default_timezone()).strftime(
                            "%Y-%m-%d %H:%M:%S %Z"))

            with transaction.atomic():
                parser = GedcomImporterCumulate(gedcom_name, parsed)
                logger.info('Done analyzing %s' % filename)

            return (True, "\n".join(parser.errors))

        except Invalid_Gedcom as e:
            logger.error("Exception while parsing GEDCOM:\n%s" % (e, ))
            return (False, e.msg)
        except Exception as e:
            logger.error("Unexpected Exception during parsing %s"
                         % traceback.format_exc())
            return (False, traceback.format_exc())
