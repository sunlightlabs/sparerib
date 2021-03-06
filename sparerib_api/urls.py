from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page
from views import AgencyView, DocketView, DocumentView, EntityView, EntityDocketView, EntitySummaryView, RawTextView, FileProxyView, NotFoundView

from search import DocumentSearchResultsView, FRSearchResultsView, NonFRSearchResultsView, DocketSearchResultsView, EntitySearchResultsView, AgencySearchResultsView, DefaultSearchResultsView

from clustering import DocketHierarchyView, SingleClusterView, DocumentClusterView, DocumentClusterChainView, HierarchyTeaserView

HOUR_CACHE = cache_page(3600)

urlpatterns = patterns('',
    # resource pages
    url(r'^agency/(?P<agency>[A-Z-]+$)', HOUR_CACHE(AgencyView.as_view()), name='agency-view'),
    url(r'^docket/(?P<docket_id>[A-Z0-9_-]+$)', HOUR_CACHE(DocketView.as_view()), name='docket-view'),
    url(r'^document/(?P<document_id>[A-Z0-9_-]+$)', DocumentView.as_view(), name='document-view'),
    url(r'^(?P<type>organization|individual|politician|entity)/(?P<entity_id>[a-f0-9-]+$)', EntityView.as_view(), name='entity-view'),
    # brisket-specific entity endpoints
    url(r'^(?P<entity_type>organization|individual|politician|entity)/(?P<entity_id>[a-f0-9-]+)/(?P<document_type>mentions|submissions)_in_docket/(?P<docket_id>[A-Z0-9_-]+$)', EntityDocketView.as_view(), name='entity-docket-view'),
    url(r'^entity_list$', EntitySummaryView.as_view(), name='entity-list'),
    
    # search
    url(r'^search/document/(?P<query>.*$)', DocumentSearchResultsView.as_view(), name='search-documents-view'),
    url(r'^search/document-fr/(?P<query>.*$)', FRSearchResultsView.as_view(), name='search-fr-documents-view'),
    url(r'^search/document-non-fr/(?P<query>.*$)', NonFRSearchResultsView.as_view(), name='search-non-fr-documents-view'),
    url(r'^search/docket/(?P<query>.*$)', DocketSearchResultsView.as_view(), name='search-dockets-view'),
    url(r'^search/agency/(?P<query>.*$)', AgencySearchResultsView.as_view(), name='search-agency-view'),
    url(r'^search/entity/(?P<query>.*$)', EntitySearchResultsView.as_view(), name='search-entity-view'),
    url(r'^search/(?P<query>.*$)', DefaultSearchResultsView.as_view(), name='search-default-view'),

    # raw text and documents
    url(r'^document/(?P<document_id>[A-Z0-9_-]+)/view_(?P<file_type>[0-9a-z]+)\.(?P<output_format>[0-9a-z]+)$', RawTextView.as_view(), name='raw-text-view', kwargs={'view_type': 'view'}),
    url(r'^document/(?P<document_id>[A-Z0-9_-]+)/attachment_(?P<object_id>[A-Z0-9a-z]+)/view_(?P<file_type>[0-9a-z]+)\.(?P<output_format>[0-9a-z]+)$', RawTextView.as_view(), name='raw-text-view', kwargs={'view_type': 'attachment'}),
    url(r'^document/(?P<document_id>[A-Z0-9_-]+)/file_proxy/(?P<object_id>[A-Z0-9a-z]+)\.(?P<file_type>[0-9a-z]+)$', FileProxyView.as_view(), name='file-proxy-view'),

    # clusters
    url(r'^docket/(?P<docket_id>[A-Z0-9_-]+)/hierarchy$', DocketHierarchyView.as_view(), name='docket-hierarchy'),
    url(r'^docket/(?P<docket_id>[A-Z0-9_-]+)/cluster/(?P<cluster_id>\d+)$', SingleClusterView.as_view(), name='single-cluster'),
    url(r'^docket/(?P<docket_id>[A-Z0-9_-]+)/cluster/(?P<cluster_id>\d+)/document/(?P<document_id>\d+)$', DocumentClusterView.as_view(), name='document-cluster'),
    url(r'^docket/(?P<docket_id>[A-Z0-9_-]+)/clusters_for_document/(?P<document_id>\d+)$', DocumentClusterChainView.as_view(), name='document-cluster'),
    # cluster teasers
    url(r'^docket/(?P<item_id>[A-Z0-9_-]+)/hierarchy_teaser$', HierarchyTeaserView.as_view(), name='docket-hierarchy', kwargs={'item_type': 'docket'}),
    url(r'^document/(?P<item_id>[A-Z0-9_-]+)/hierarchy_teaser$', HierarchyTeaserView.as_view(), name='docket-hierarchy', kwargs={'item_type': 'document'}),

    # explicitly do our own fall-through to make sure we don't serve up the Backbone HTML on API calls
    url(r'', NotFoundView.as_view()),
)
