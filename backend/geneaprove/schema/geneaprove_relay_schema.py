import graphene
from graphene.relay import Connection
from graphene import Node, String
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene_django_optimizer as gql_optimizer
from geneaprove.models import Persona, Place, Place_Part, Place_Part_Type, Surety_Scheme, Surety_Scheme_Part


class Persona_Node(DjangoObjectType):
    class Meta:
        model = Persona
        interfaces = (Node, )

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'display_name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'birthISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'deathISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'marriageISODate': ['exact', 'icontains', 'istartswith', 'iendswith'],
            # 'sex': ['exact'],
        }


class Place_Node(DjangoObjectType):
    class Meta:
        """Meta data for the model"""
        model = Place
        interfaces = (Node, )
        # ordering = ("date_sort",)

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date_sort': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'parent_place': ['exact'],
        }

class PlaceConnection(Connection):
    extra = String()

    class Meta:
        node = Place_Node

    class Edge:
        other = String()

class Place_Part_Node(DjangoObjectType):
    """Specific information about a place."""
    class Meta:
        """Meta data for the model"""
        model = Place_Part
        interfaces = (Node, )
        # ordering = ('sequence_number', 'name')
        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'place': ['exact'],
            'type': ['exact'],
            'sequence_number': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }

class Place_Part_Type_Node(DjangoObjectType):
    """Contains information about various schemes for organizing place data."""
    class Meta:
        """Meta data for the model"""
        model = Place_Part_Type
        interfaces = (Node, )
        filter_fields = '__all__'


class Surety_Scheme_Node(DjangoObjectType):
    class Meta:
        model = Surety_Scheme
        interfaces = (Node, )

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }


class Surety_Scheme_Part_Node(DjangoObjectType):
    """An element of a Surety_Scheme."""
    class Meta:
        """Meta data for the model."""
        model = Surety_Scheme_Part
        interfaces = (Node, )
        # ordering = ('sequence_number', 'name')

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith'],
            'description': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'scheme': ['exact'],
            'sequence_number': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }


class Query(object):
    persona = Node.Field(Persona_Node)
    all_personas = DjangoFilterConnectionField(Persona_Node)
    def resolve_all_personas(self, info, **kwargs):
        return gql_optimizer.query(Persona.objects.all(), info)        

    place = Node.Field(Place_Node)
    all_places = DjangoFilterConnectionField(Place_Node)
    def resolve_all_places(self, info, **kwargs):
        return gql_optimizer.query(Place.objects.all(), info)        

    place_part = Node.Field(Place_Part_Node)
    all_place_parts = DjangoFilterConnectionField(Place_Part_Node)
    def resolve_all_place_parts(self, info, **kwargs):
        return gql_optimizer.query(Place_Part.objects.all(), info)        

    place_part_type = Node.Field(Place_Part_Type_Node)
    all_place_part_types = DjangoFilterConnectionField(Place_Part_Type_Node)
    def resolve_all_place_part_types(self, info, **kwargs):
        return gql_optimizer.query(Place_Part_Type.objects.all(), info)        

    surety_scheme_part = Node.Field(Surety_Scheme_Part_Node)
    all_surety_scheme_parts = DjangoFilterConnectionField(Surety_Scheme_Part_Node)
    def resolve_all_surety_scheme_parts(self, info, **kwargs):
        return gql_optimizer.query(Surety_Scheme_Part.objects.all(), info)        
