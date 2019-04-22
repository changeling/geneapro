import graphene
from graphene.relay import Connection
from graphene import Node, String
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene_django_optimizer as gql_optimizer
from geneaprove.models import (
    Persona, Characteristic, Characteristic_Part, Characteristic_Part_Type, Event, Event_Type, Event_Type_Role, Part_Type, Place, Place_Part,
    Place_Part_Type, P2P, P2P_Type, P2C, P2E, Surety_Scheme, Surety_Scheme_Part)


class Place_Type(DjangoObjectType):
    class Meta:
        model = Place
        interfaces = (Node, )
        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date_sort': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'parent_place': ['exact'],
        }


class Place_Part_Type_Node(DjangoObjectType):
    class Meta:
        model = Place_Part_Type
        interfaces = (Node, )
        filter_fields = '__all__'


class Place_Part_Node(DjangoObjectType):
    class Meta:
        model = Place_Part
        interfaces = (Node, )
        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'place': ['exact'],
            'sequence_number': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }

    # place = models.ForeignKey(Place, related_name="parts", on_delete=models.CASCADE)
    # type = models.ForeignKey(Place_Part_Type, on_delete=models.CASCADE)

class Characteristic_Part_Type_Node(DjangoObjectType):
    class Meta:
        model = Characteristic_Part_Type
        interfaces = (Node, )
        filter_fields = '__all__'
    # is_name_part = models.BooleanField(default=False)
    # PK_sex = lazy_lookup(gedcom='SEX')
    # PK_img = lazy_lookup(gedcom='_IMG')
    # PK_given_name = lazy_lookup(gedcom='GIVN')
    # PK_surname = lazy_lookup(gedcom='SURN')


class Characteristic_Node(DjangoObjectType):
    class Meta:
        model = Characteristic
        interfaces = (Node, )
        filter_fields = '__all__'


    # name = 
    # place = models.ForeignKey(Place, null=True, on_delete=models.CASCADE)
    # date = 
    # date_sort = 
    # place =     characteristic = graphene.List(Place_Node)


class Characteristic_Part_Node(DjangoObjectType):
    class Meta:
        model = Characteristic_Part
        interfaces = (Node, )
        filter_fields = '__all__'


    # characteristic = models.ForeignKey(
    #     Characteristic, related_name="parts", on_delete=models.CASCADE)
    # type = models.ForeignKey(
    #     Characteristic_Part_Type, on_delete=models.CASCADE)
    # name = 
    # sequence_number = 

    characteristic = graphene.Field(Characteristic_Node)
    type = graphene.Field(Characteristic_Part_Type_Node)


class Event_Object(DjangoObjectType):
    class Meta:
        model = Event
        interfaces = (Node, )
        filter_fields = '__all__'
    # event = graphene.Field(Event_Type)


class Event_Type_Role_Object(DjangoObjectType):
    class Meta:
        model = Event_Type_Role
        interfaces = (Node, )
        # filter_fields = '__all__'
        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith'],
        }


class Event_Type_Object(DjangoObjectType):
    class Meta:
        model = Event_Type
        interfaces = (Node, )
        filter_fields = '__all__'

    role = graphene.Field(Event_Type_Role_Object)


class P2C_Node(DjangoObjectType):
    class Meta:
        model = P2C
        interfaces = (Node, )

        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'person': ['exact'],
            'characteristic': ['exact'],
        }

    characteristics = graphene.List(Characteristic_Node)
    def resolve_characteristics(self, info):
        return gql_optimizer.query(self.characteristics.all())

class Persona_Node(DjangoObjectType):
    class Meta:
        model = Persona
        interfaces = (Node, )

        # filter_fields = '__all__'

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'display_name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'main': ['exact'],
            # 'birthISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'deathISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'marriageISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'sex': ['exact'],
        }

class P2E_Node(DjangoObjectType):
    class Meta:
        model = P2E
        interfaces = (Node, )

        # filter_fields = '__all__'

        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'rationale': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'disproved': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'person': ['exact'],
            'event': ['exact'],
            'role': ['exact'],
        }


class P2P_Type_Node(DjangoObjectType):
    class Meta:
        model = P2P_Type
        interfaces = (Node, )

        # filter_fields = '__all__'

        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'sameAS': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }

class P2P_Node(DjangoObjectType):
    class Meta:
        model = P2P
        interfaces = (Node, )

        # filter_fields = '__all__'

        filter_fields = {
            'id': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'person1': ['exact'],
            'person2': ['exact'],
            'type': ['exact'],
        }

class Query(object):
    persona = graphene.Field(Persona_Node)
    all_personas = graphene.List(Persona_Node)
    def resolve_persona(self, info, **kwargs):
        return gql_optimizer.query(Persona, info)        
    def resolve_all_personas(self, info, **kwargs):
        return gql_optimizer.query(Persona.objects.all(), info)        

    persona_node = DjangoFilterConnectionField(Persona_Node)
    all_persona_nodes = DjangoFilterConnectionField(Persona_Node)
    def resolve_persona_node(self, info, **kwargs):
        return gql_optimizer.query(Persona, info)        
    def resolve_all_persona_nodes(self, info, **kwargs):
        return gql_optimizer.query(Persona.objects.all(), info)        

    characteristic = graphene.Field(Characteristic_Node)
    all_characteristics = graphene.List(Characteristic_Node)
    def resolve_characteristic(self, info):
        return gql_optimizer.query(Characteristic, info)
    def resolve_all_places(self, info):
        return gql_optimizer.query(Characteristic.objects.all(), info)

    characteristic_node = Node.Field(Characteristic_Node)
    all_characteristic_nodes = DjangoFilterConnectionField(Characteristic_Node)
    def resolve_characteristic_node(self, info, **kwargs):
        return gql_optimizer.query(Characteristic, info)        
    def resolve_all_characteristic_nodes(self, info, **kwargs):
        return gql_optimizer.query(Characteristic.objects.all(), info)        

    place = graphene.Field(Place_Type)
    all_places = graphene.List(Place_Type)
    def resolve_place(self, info):
        return gql_optimizer.query(Place, info)
    def resolve_all_places(self, info):
        return gql_optimizer.query(Place.objects.all(), info)

    place_node = DjangoFilterConnectionField(Place_Type)
    all_place_nodes = DjangoFilterConnectionField(Place_Type)
    def resolve_place_node(self, info, **kwargs):
        return gql_optimizer.query(Place, info)
    def resolve_all_place_nodes(self, info, **kwargs):
        return gql_optimizer.query(Place.objects.all(), info)        
  
    event = graphene.Field(Event_Object)
    all_events = graphene.List(Event_Object)
    def resolve_event(self, info):
        return gql_optimizer.query(Event, info)
    def resolve_all_events(self, info, **kwargs):
        return gql_optimizer.query(Event.objects.all(), info)

    event_node = DjangoFilterConnectionField(Event_Object)
    all_event_nodes = DjangoFilterConnectionField(Event_Object)
    def resolve_event_node(self, info, **kwargs):
        return gql_optimizer.query(Event, info)
    def resolve_all_event_nodes(self, info, **kwargs):
        return gql_optimizer.query(Event.objects.all(), info)
