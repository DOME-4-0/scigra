from rdflib import Graph, Namespace, OWL, RDF, URIRef, Literal, XSD
from rdflib import plugin, BNode, URIRef, Literal
# from rdflib.serializer import Serializer
import requests, json
from SPARQLWrapper import JSON, SPARQLWrapper


class Scigra:
    """ From  SimPhoNy-Scigra Package
        simple convenience wrapper around RDFLIB Graph()
        - make sure URI is correctly represented not Literal
        - remove the need for double brackets (tuple),
        - shorten the bind process
        should be later added to pip and directly installed as req.
        Note, it is repeated in provider registration and perhaps other places.

        """

    def __init__(self):
        self.g = Graph()

    def safe_uri(self, value):
        # Warning does not handle blank nodes properly yet, needs some huristics, ex name as _: or b...
        # return value if isinstance(value, Literal) else URIRef(value)
        return value if isinstance(value, Literal) else Literal(value) if isinstance(value, str) else URIRef(value)

    def add(self, s, p, o):
        # warining does not handle blank nodes properly yet.
        self.g.add((self.safe_uri(s), self.safe_uri(p), self.safe_uri(o)))
        # print(self.safe_uri(s), self.safe_uri(p), self.safe_uri(o))

    @property
    def jsonld(self):
        """ returns a jsonld as a string"""
        json_ld = self.g.serialize(format="json-ld", indent=4)
        print(f"Serialized JSON-LD: {json_ld}")

        return (json_ld)

    def __iter__(self):
        return iter(self.g)

    @property
    def dict(self):
        """ returns a dict as a string"""
        _dict = json.loads(self.g.serialize(format="json-ld"))
        if isinstance(_dict, list) and len(_dict) == 1:
            return _dict[0]
        else:
            return _dict

    def bind(self, prefix, iri):
        ns = Namespace(iri)
        self.g.bind(prefix, ns)
        return ns

    def print(self):
        print(self.g.serialize(format="json-ld"))

    def load(self, p, f):
        self.g.parse(p, f)

    @property
    def in_graph(self):
        catalog_in_graph = {
            "@id": "http://dome40.io/dataset/data/dome-all-data",
            "@graph": [self.dict]
        }
        return (catalog_in_graph)


class SparqlQuery:
    """
    return a jsonld for a query (for now server etc are hard coded
    """

    def __init__(self, q=None):
        """
        define server, graph, json, etc, some book keeping...initialise scigraph ...
        """
        self.results_json = None
        self.query = q
        self.graph = Graph()

    def _run_query(self):
        sparql = SPARQLWrapper(f"http://localhost:3030/dataset/sparql")
        sparql.setQuery(self.query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        self.results_json = results

    def _convert_rdf_to_graph(self):
        """
        Converts SPARQL JSON results to an RDFLib Graph as an intermediate step to get proper json-ld
        assumes also use of subject predicate object as bindings
        """
        for result in self.results_json["results"]["bindings"]:
            s_value = result["subject"]["value"]
            p_value = result["predicate"]["value"]
            o_value = result["object"]["value"]

            s = BNode(s_value) if result["subject"]["type"] == "bnode" else URIRef(s_value)
            p = URIRef(p_value)

            if result["object"]["type"] == "bnode":
                o = BNode(o_value)
            elif result["object"]["type"] == "uri":
                o = URIRef(o_value)
            elif result["object"]["type"] == "literal":
                if "datatype" in result["object"]:
                    o = Literal(o_value, datatype=URIRef(result["object"]["datatype"]))
                elif "xml:lang" in result["object"]:
                    o = Literal(o_value, lang=result["object"]["xml:lang"])
                else:
                    o = Literal(o_value)
            else:
                o = Literal(o_value)

            self.graph.add((s, p, o))

    def get_rdf_graph(self):
        self._run_query()
        self._convert_rdf_to_graph()
        return(self.graph)

    def get_jsonld(self):
        g=self.get_rdf_graph()
        js=g.serialize(format="json-ld", indent=4)
        return(js)
