from rdflib import Graph, Namespace, OWL, RDF, URIRef, Literal, XSD
from rdflib import plugin, BNode, URIRef, Literal
# from rdflib.serializer import Serializer
import requests, json
from SPARQLWrapper import JSON, SPARQLWrapper
from rdflib.compare import isomorphic, to_isomorphic, graph_diff



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
        # return value if isinstance(value, Literal) else URIRef(value) # old option, new one tries to handle literal
        # which is already a literal!
        return value if isinstance(value, Literal) else Literal(value) if isinstance(value, str) else URIRef(value)

    def add(self, s, p, o):
        # warning: also does not handle blank nodes properly yet, since safe_uri does not.
        # this issue was found when converting the dome 4.0 eco system to jsonld
        self.g.add((self.safe_uri(s), self.safe_uri(p), self.safe_uri(o)))
        # print(self.safe_uri(s), self.safe_uri(p), self.safe_uri(o)) # debug

    @property
    def jsonld(self):
        """ returns a jsonld as a string """
        json_ld = self.g.serialize(format="json-ld", indent=4)
        print(f"Serialized JSON-LD: {json_ld}")

        return (json_ld)

    def __iter__(self):
        # iterator, is essentially that of RDFlib.
        return iter(self.g)

    @property
    def dict(self):
        """ returns a dict """
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
        """
        needed for dome 4.0 graph provenance
        """
        catalog_in_graph = {
            # should not be statics and hardcoded!
            "@id": "http://dome40.io/dataset/data/dome-all-data",
            "@graph": [self.dict]
        }
        return (catalog_in_graph)


class ScigraDB:
    """
    Wrapper to query
    query and return results as jsonld graph
    Note: Server is hardcoded, but should not be.
    """

    def __init__(self, q=None):
        """
        define server, graph, json, etc, some book keeping...initialise scigraph ...
        """
        self.results_json = None
        self.query = q
        self._graph = Graph()  # should be class Scigra

    def run_query(self):
        """
        take the self.query, activate it and define the result as a json
        """
        if self.query == None:
            raise TypeError("please provide query! self.q=...")
        sparql = SPARQLWrapper(f"http://localhost:3030/dataset/sparql")
        sparql.setQuery(self.query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        self.results_json = results

    def _convert_to_jsonld_graph(self):
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

            self._graph.add((s, p, o))

    def get_rdflib_graph(self):
        self.run_query()
        self._convert_to_jsonld_graph()
        return self._graph

    def get_jsonld(self):
        g=self.get_rdf_graph()
        js=g.serialize(format="json-ld", indent=4)
        return(js)


def dump_nt_sorted(g):
    for l in sorted(g.serialize(format='nt').splitlines()):
        if l: print(l)

def compare_graphs (g1, g2):
    g1 = g1.g if isinstance(g1, Scigra) else g1
    g2 = g2.g if isinstance(g2, Scigra) else g2

    if isomorphic(g1, g2):
        print("The graphs are the same.")
    else:
        print("The graphs are different.")

    iso1 = to_isomorphic(g1)
    iso2 = to_isomorphic(g2)

    print(f"Testing iso1==iso2: {iso1==iso2}")

    # Perform the graph_diff
    in_both, in_first, in_second = graph_diff(iso1, iso2)

    # Print the results
    print(f"Present in both: {len(in_both)}")

    print(f"Present in first: {len(in_first)}")

    print(f"Present in second: {len(in_second)}")

    print(f"size of first {len(iso1)}, size of second {len(iso2)}")
    #dump_nt_sorted(in_first)

    print("\nOnly in second:")
    #dump_nt_sorted(in_second)

    return {"in both" : in_both, "in first": in_first, "in second": in_second}

