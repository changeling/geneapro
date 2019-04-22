import graphene
from graphene import Connection, ID, Interface, List, String
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene_django_optimizer as gql_optimizer
from geneaprove.models import Place, Place_Part, Place_Part_Type


class PlaceType(DjangoObjectType):
    class Meta:
        model = Place

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'date_sort': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'parent_place': ['exact'],
        }


# class Place_Interface(Interface):
#     id = ID(required=True)
#     name = String(required=True)
#     place_parts = List(lambda: Place_Part)


# class PlaceConnection(Connection):
#     extra = String()

#     class Meta:
#         place = PlaceType


class Place_Part(DjangoObjectType):
    """Specific information about a place."""
    class Meta:
        """Meta data for the model"""
        model = Place_Part

        filter_fields = {
            'id':  ['exact', 'icontains'],
            'name': ['exact', 'icontains', 'istartswith', 'iendswith'],
            'place': ['exact'],
            'type': ['exact'],
            'sequence_number': ['exact', 'icontains', 'istartswith', 'iendswith'],
        }


class Place_Part_Type(DjangoObjectType):
    """Contains information about various schemes for organizing place data."""
    class Meta:
        """Meta data for the model"""
        model = Place_Part_Type

        filter_fields = '__all__'


class Query(object):
    place = graphene.Field(PlaceType)
    # all_places = graphene.List(PlaceType)
    all_places = DjangoFilterConnectionField(PlaceType)
    def resolve_all_places(self, info, **kwargs):
        return gql_optimizer.query(Place.objects.all(), info)        

    place_part = graphene.Field(Place_Part)
    # all_place_parts = graphene.List(Place_Part)
    all_place_parts = DjangoFilterConnectionField(Place_Part)
    def resolve_all_place_parts(self, info, **kwargs):
        return gql_optimizer.query(Place_Part.objects.all(), info)        

    place_part_type = graphene.Field(Place_Part_Type)
    # all_place_part_types = graphene.List(Place_Part_Type)
    all_place_part_types = DjangoFilterConnectionField(Place_Part_Type)
    def resolve_all_place_part_types(self, info, **kwargs):
        return gql_optimizer.query(Place_Part_Type.objects.all(), info)        
