from django.urls import path
from .views import DisagreementsView, OrgsListView, ReasonsListView

urlpatterns = [
    path("disagreements/", DisagreementsView.as_view(), name="disagreements"),
    path("orgs/", OrgsListView.as_view(), name="orgs"),
    path("reasons/", ReasonsListView.as_view(), name="reasons"),
]
