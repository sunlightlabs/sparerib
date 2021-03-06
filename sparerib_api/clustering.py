from rest_framework.views import APIView
from rest_framework.response import Response
from analysis.corpus import get_dual_corpora_by_metadata, find_doc_in_hierarchy, trace_doc_in_hierarchy
from analysis.utils import profile
from django.conf import settings
from django.http import Http404
from django.core.cache import cache

from django.db import connection
import psycopg2.extras

import itertools
try:
    import numpypy
except:
    pass
import numpy

from regs_models import *

DEFAULT_CUTOFF = getattr(settings, 'DEFAULT_CLUSTER_CUTOFF', 0.9)


class CommonClusterView(APIView):
    _cutoff = None
    _clusters = None
    _corpus = None

    @property
    def cutoff(self):
        if self._cutoff is None:
            if 'cutoff' in self.request.QUERY_PARAMS:
                self._cutoff = float(self.request.QUERY_PARAMS['cutoff'])
            else:
                self._cutoff = DEFAULT_CUTOFF
        return self._cutoff

    @property
    def corpus(self):
        if self._corpus is None:
            self._corpus = get_dual_corpora_by_metadata('docket_id', self.kwargs['docket_id'])
            if not self._corpus:
                # todo: better error handling
                raise Http404("Couldn't find analysis for docket %s" % self.kwargs['docket_id'])
        return self._corpus

    def dispatch(self, *args, **kwargs):
        # make sure the fancy postgres stuff works right
        connection.cursor()
        psycopg2.extras.register_hstore(connection.connection)
        psycopg2.extras.register_composite('int_bounds', connection.connection)

        return super(CommonClusterView, self).dispatch(*args, **kwargs)




class DocketHierarchyView(CommonClusterView):
    @profile
    def get(self, request, docket_id):
        docket = Docket.objects.get(id=docket_id)

        hierarchy = self.corpus.hierarchy(request.GET.get('require_summaries', "").lower()=="true")
        total_clustered = sum([cluster['size'] for cluster in hierarchy])
        
        out = {
            'cluster_hierarchy': sorted(hierarchy, key=lambda x: x['size'], reverse=True),
            'stats': {
                'clustered': total_clustered,
                'unclustered': docket.stats['count'] - total_clustered if 'count' in docket.stats else None,
                'date_range': docket.stats['date_range'] if 'date_range' in docket.stats else None
            },
            'prepopulate': None
        }

        # populate agency info
        agency = docket.agency or docket.id.split("-")[0]
        if agency:
            agency_meta = list(Agency.objects(id=agency).only("name"))
            if agency_meta:
                out['stats']['agency'] = {
                    'id': agency,
                    'name': agency_meta[0].name,
                    'url': '/agency/%s' % agency
                }
            else:
                out['stats']['agency'] = None

        # choose a cluster and document to prepopulate if one hasn't been requested
        prepop = int(request.GET.get('prepopulate_document', -1))
        if prepop > -1:
            pp_cluster = find_doc_in_hierarchy(hierarchy, prepop, self.cutoff)
            if pp_cluster:
                out['prepopulate'] = {
                    'document': prepop,
                    'cluster': pp_cluster['name'],
                    'cutoff': self.cutoff
                }
        if not out['prepopulate'] and out['stats']['clustered'] > 0:
            pp_cluster = find_doc_in_hierarchy(hierarchy, out['cluster_hierarchy'][0]['name'], out['cluster_hierarchy'][0]['cutoff'])
            out['prepopulate'] = {
                'document': pp_cluster['members'][0],
                'cluster': pp_cluster['name'],
                'cutoff': out['cluster_hierarchy'][0]['cutoff']
            }

        remove_members(out['cluster_hierarchy'])

        return Response(out)

def remove_members(hierarchy):
    """Remove doc IDs from cluster hierarchy.

    IDs are needed for some internal operations, but aren't
    needed in browser. Large dockets could have tense of thousands
    of IDs, making API results unnecessarily large if not removed.
    """
    for c in hierarchy:
        del c['members']
        remove_members(c['children'])


class HierarchyTeaserView(CommonClusterView):
    @profile
    def get(self, request, item_id, item_type="docket"):
        if item_type == "document":
            doc = Doc.objects.only("docket_id").get(id=item_id)
            self.kwargs['docket_id'] = doc.docket_id
        else:
            self.kwargs['docket_id'] = item_id

        hierarchy = self.corpus.hierarchy()

        out = {
            'docket_teaser': {
                '0.5': {'count': self._count_clusters(hierarchy, 0.5)},
                '0.8': {'count': self._count_clusters(hierarchy, 0.8)}
            }
        }

        if item_type == 'document':
            out['document_teaser'] = None
            docs = self.corpus.docs_by_metadata('document_id', item_id)
            if docs:
                out['document_teaser'] = {}
                doc_id = docs[0]

                cluster05 = find_doc_in_hierarchy(hierarchy, doc_id, 0.5)
                if cluster05:
                    out['document_teaser'] = {'0.5': {'count': cluster05['size'], 'id': doc_id}}
                    
                    cluster08 = find_doc_in_hierarchy(hierarchy, doc_id, 0.8)
                    if cluster08:
                        out['document_teaser']['0.8'] = {'count': cluster08['size'], 'id': doc_id}

        return Response(out)

    def _count_clusters(self, hierarchy, cutoff):
        count = 0

        for cluster in hierarchy:
            if cluster['cutoff'] == cutoff:
                count += 1

            if cluster['cutoff'] < cutoff:
                count += self._count_clusters(cluster['children'], cutoff)

        return count


class SingleClusterView(CommonClusterView):
    @profile
    def get(self, request, docket_id, cluster_id):
        cluster_id = int(cluster_id)
        
        h = self.corpus.hierarchy()
        cluster = find_doc_in_hierarchy(h, cluster_id, self.cutoff)

        # consider caching for very large clusters
        _metadatas = lambda: dict(self.corpus.doc_metadatas(cluster['members']))
        members = tuple(cluster['members'])
        if len(members) > 1000:
            key = 'sparerib_api.clustering.cluster-%s-%s-%s' % (docket_id, cluster_id, hash(members))
            
            metadatas = cache.get(key)
            if not metadatas:
                metadatas = _metadatas()
                cache.set(key, metadatas)
        else:
            # it's little; don't cache
            metadatas = _metadatas()

        return Response({
            'id': cluster['name'],
            'documents': [{
                'id': doc_id,
                'title': metadatas[doc_id]['title'],
                'submitter': ', '.join([metadatas[doc_id][field] for field in ['submitter_name', 'submitter_organization'] if field in metadatas[doc_id] and metadatas[doc_id][field]])
            } for doc_id in cluster['members']]
        })


class DocumentClusterView(CommonClusterView):
    @profile
    def get(self, request, docket_id, cluster_id, document_id):
        document_id = int(document_id)
        cluster_id = int(cluster_id)

        h = self.corpus.hierarchy()
        cluster = find_doc_in_hierarchy(h, cluster_id, self.cutoff)['members']

        doc = self.corpus.doc(document_id)
        text = doc['text']
        raw_phrases = self.corpus.phrase_overlap(document_id, cluster)
        
        frequencies = numpy.zeros(len(text), 'l')
        for phrase in raw_phrases.values():
            for occurrence in phrase['indexes']:
                frequencies[occurrence.start:occurrence.end] = numpy.maximum(frequencies[occurrence.start:occurrence.end], phrase['count'])

        freq_ranges = [(f[0], len(list(f[1]))) for f in itertools.groupby(frequencies)]
        cluster_size = float(len(cluster))

        components = []
        cursor = 0
        for fr in freq_ranges:
            components.append((fr[0], text[cursor:cursor + fr[1]]))
            cursor += fr[1]

        html = ''.join(['<span style="background-color:rgba(160,211,216,%s)">%s</span>' % (round(p[0]/cluster_size, 2), p[1]) for p in components])
        html = html.replace("\n", "<br />")
        return Response({
            'metadata': {
                'title': doc['metadata'].get('title', None),
                'submitter': ', '.join([doc['metadata'][field] for field in ['submitter_name', 'submitter_organization'] if field in doc['metadata'] and doc['metadata'][field]]),
                'document_id': doc['metadata'].get('document_id', None),
            },
            'frequency_html': html,
            'truncated': len(doc['text']) == 10000
        })

class DocumentClusterChainView(CommonClusterView):
    @profile
    def get(self, request, docket_id, document_id):
        document_id = int(document_id)

        h = self.corpus.hierarchy()

        return Response({
            'clusters': [{
                'cutoff': round(entry[0], 2),
                'id': entry[1],
                'size': entry[2]
            } for entry in trace_doc_in_hierarchy(h, document_id)]
        })

