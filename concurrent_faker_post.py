import sys
import datetime
from faker import Faker
from py2neo import Node, Relationship, Graph
from concurrent.futures import ThreadPoolExecutor, as_completed


class RandomPost:

    __fake = Faker()
    graph = None

    def __init__(self, host="35.200.1.162", username="neo4j", password="fullspeed", port="7474"):
        self.graph = Graph("http://{}:{}@{}:{}/db/data/".format(username, password, host, port))

    def get_random_user(self):
        """ cypher query on random user based on random id return 1 """
        return self.graph.data("MATCH (UserNode:UserNode) "
                               "WITH UserNode, rand() AS randomId "
                               "RETURN * ORDER BY randomId LIMIT 1").pop()

    def get_random_place(self):
        """ cypher query on random place based on location country (Japan, Philippines and Taiwan) return 1 """
        return self.graph.data("MATCH (LocationNode:LocationNode)-[:HAS_PLACE]->(PlaceNode:PlaceNode) "
                               "WITH LocationNode, PlaceNode, rand() AS randomId "
                               "WHERE LocationNode.country='Japan'  OR LocationNode.country='Philippines' "
                               "OR LocationNode.country='Taiwan' "
                               "RETURN ID(LocationNode) AS locationId, ID(PlaceNode) AS placeId, "
                               "LocationNode, PlaceNode ORDER BY randomId LIMIT 1").pop()

    def generate(self, place_node, user_found, worker_id):
        graph = self.graph
        print("Worker {} started".format(worker_id))
        """ set the current date without microsecond because it's not acceptable to laravel datetime format """
        date = str(datetime.datetime.today().replace(microsecond=0))

        """ create dummy Post node object """
        post_node = Node("PostNode", caption=self.__fake.text(), created_at=date, updated_at=date)

        """ create 3 relationships between post node object to the usernode as AUTHOR
            place node to post node as HAS_POST
            post node to place node as LOCATED_AT
        """
        rel1 = Relationship(post_node, "AUTHOR", user_found["UserNode"], created_at=date, updated_at=date)
        rel2 = Relationship(place_node["PlaceNode"], "HAS_POST", post_node, created_at=date, updated_at=date)
        rel3 = Relationship(post_node, "LOCATED_AT", place_node["PlaceNode"], created_at=date, updated_at=date)

        """ save the created objects to neo4j graph """
        graph.create(post_node)
        graph.create(rel1)
        graph.create(rel2)
        graph.create(rel3)

        print("Worker done".format(worker_id))
        return post_node


def random_place():
    try:
        return random_post.get_random_place()
    finally:
        print('random place success!')


def random_user():
    try:
        return random_post.get_random_user()
    finally:
        print('random user success!')


def worker_resource(executor, worker_id):
    """ fetch the thread executor and process another work for getting random place and random user """
    print("worker resource {} started".format(worker_id))
    get_random_place = executor.submit(random_place)
    get_random_user = executor.submit(random_user)
    if not get_random_place.done() and not get_random_user.done():
        # print("get_random_place and get_random_user are processing...")
        pass
    if True:
        try:
            return get_random_place.result(), get_random_user.result()
        finally:
            print('worker resource success!')


def generate_post(worker_id):
    """ For I/O-bound workloads because this generator uses tremendous amount of calculation """
    with ThreadPoolExecutor(max_workers=10) as tpe:
        """ get the random place and user resources as a tuple (place, user) 
        and pass the work executor to be used for another thread process
        """
        resources = tpe.submit(worker_resource, tpe, worker_id)
        if not resources.done():
            print("worker_resource is processing...")
            pass
        if True:
            """ create a dummy post using the place and user resources"""
            post_generator_resource = tpe.submit(
                random_post.generate,
                resources.result()[0],
                resources.result()[1],
                worker_id)
            if not post_generator_resource.done():
                print('generate_post is processing...')
                pass

            if True:
                try:
                    """ return the result """
                    return post_generator_resource.result()
                finally:
                    print('generate post success!')


def main(worker_id):
    """ For I/O-bound workloads
    execute a recursion
    """
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_post_resource = executor.submit(generate_post, worker_id)
        if as_completed(future_post_resource):
            print("Successfully generated post!")
            print(future_post_resource.result())
            main(worker_id + 1)

if __name__ == '__main__':
    """ set recursionlimit for infinite recursion function """
    sys.setrecursionlimit(1000)
    random_post = RandomPost()
    main(329)
