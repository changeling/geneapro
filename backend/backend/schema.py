import graphene
from graphene_django.debug import DjangoDebug
from geneaprove.schema import geneaprove_persona_schema

class Query(geneaprove_persona_schema.Query, graphene.ObjectType):
    # debug = graphene.Field(DjangoDebug, name='__debug')
    # This class will inherit from multiple Queries
    # as we begin to add more apps to our project
    pass

schema = graphene.Schema(query=Query)
