import requests
import json
import datetime
import time
import os
import sys
from py2neo import Node, Relationship, Graph


class Place:
    query = None
    country = "Japan"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    lat = "36.204824"
    lng = "138.252924"
    global place_api_key
    key = None
    filename = None
    next_page_token = None
    __result = []
    __PlaceNodeLabel = "PlaceNode"
    __LocationNodeLabel = "LocationNode"
    type_index = 0
    place_types = ["country", "locality", "political", "accounting", "airport", "amusement_park", "aquarium",
                   "art_gallery", "atm", "bakery", "bank", "bar", "beauty_salon", "bicycle_store", "book_store",
                   "bowling_alley", "bus_station", "cafe", "campground", "car_dealer", "car_rental", "car_repair",
                   "car_wash", "casino", "cemetery", "church", "city_hall", "clothing_store", "convenience_store",
                   "courthouse", "dentist", "department_store", "doctor", "electrician", "electronics_store", "embassy",
                   "fire_station", "florist", "funeral_home", "furniture_store", "gas_station", "gym", "hair_care",
                   "hardware_store", "hindu_temple", "home_goods_store", "administrative_area_level_1",
                   "administrative_area_level_2", "administrative_area_level_3", "administrative_area_level_4",
                   "administrative_area_level_5", "colloquial_area", "country", "establishment", "finance", "floor",
                   "food", "general_contractor", "geocode", "health", "intersection", "locality", "natural_feature",
                   "neighborhood", "place_of_worship", "political", "point_of_interest", "post_box", "postal_code",
                   "postal_code_prefix", "postal_code_suffix", "postal_town", "premise", "room", "route",
                   "street_address", "street_number", "sublocality", "sublocality_level_4", "sublocality_level_5",
                   "sublocality_level_3", "sublocality_level_2", "sublocality_level_1", "subpremise"]

    global secure_graph

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.key = place_api_key
        self.set_file_directory_by_country(country=self.country)
        self.reques_place()

    def set_file_directory_by_country(self, country):
        self.filename = "results/" + country + ".json"

    @staticmethod
    def find_country(
            name="Japan",
            url="https://maps.googleapis.com/maps/api/place/textsearch/json"
            ):
        global place_api_key
        params = {
            "query": name.title(),
            "types": "country",
            "key": place_api_key
        }
        print('Requesting...')
        with requests.get(url, params=params) as res:
            # get the data from the request
            print(res.url)
            return res.content.decode()

    def reques_place(self, params=None):
        print('type_index: {}'.format(self.type_index))
        print('place total: {}'.format(len(self.place_types)))
        if self.type_index < len(self.place_types):
            print('place_type: {}'.format(self.place_types[self.type_index]))
            if params is None:
                params = {
                    "types": self.place_types[self.type_index],
                    "location": "{},{}".format(self.lat, self.lng)
                }
                # if self.query is not None:
                #     params.update({"query": self.query})
                if self.next_page_token is not None:
                    params.update({"pagetoken": self.next_page_token})
                params.update({"key": place_api_key})
            # initialize start time of execution
            start_time = time.time()

            # requesting data based on parameters using with so it make sure that the request has been executed
            print('Requesting...')
            with requests.get("{}".format(self.url), params=params) as res:
                # get the data from the request
                print(res.url)
                self.__result = json.loads(res.content.decode())
                if len(self.__result["results"]):
                    for idx, val in enumerate(self.__result["results"]):
                        """ saving to neo4j database """
                        self.saving_to_neo4j(val)

                        """ saving to json file """
                        self.saving_to_json_file(val)

                        # execute time total
                        time_total_execution = time.time() - start_time
                        print('time execution {}'.format(time_total_execution))

                    """ 
                    go to next request with the same parameters, 
                    the same type_index since the current index is not done because there is still pagination returned
                    and check if google page token pagination exist. it means there are still are data to be fetch
                    """
                    if "next_page_token" in self.__result:
                        print("Go to next pagination...")
                        self.next_page_token = self.__result["next_page_token"]
                        next_token = self.next_page_token
                    else:
                        next_token = None
                        self.type_index += 1

                    Place(next_page_token=next_token,
                          country=self.country,
                          lat=self.lat,
                          lng=self.lng,
                          type_index=self.type_index,
                          filename=self.filename)

                else:
                    print('{} Results found. Proceed to next place_type.'.format(len(self.__result)))
                    Place(type_index=self.type_index + 1,
                          country=self.country,
                          lat=self.lat,
                          lng=self.lng,
                          filename=self.filename)

    def saving_to_neo4j(self, val):
        if secure_graph.find_one(self.__PlaceNodeLabel, "name", val["name"]) is None:
            print('{} not found in graph! saving...'.format(val["name"]))
            date = str(datetime.datetime.today().replace(microsecond=0))
            place_node = Node(self.__PlaceNodeLabel,
                              name=val["name"],
                              place_id=val["place_id"],
                              reference=val["reference"],
                              types=val["types"],
                              opening_hours=json.dumps(
                                  val["opening_hours"]) if "opening_hours" in val else None,
                              formatted_address=val["formatted_address"],
                              rating=val["rating"] if "rating" in val else 0,
                              photos=json.dumps(val["photos"]) if "photos" in val else None,
                              created_at=date,
                              updated_at=date)

            """since per location is unique per place. so the validation will be by place name only
            """
            location_node = Node(self.__LocationNodeLabel,
                                 country=self.country,
                                 latitude=val["geometry"]["location"]["lat"],
                                 longitude=val["geometry"]["location"]["lng"],
                                 viewport=json.dumps(val["geometry"]["viewport"]),
                                 created_at=date,
                                 updated_at=date)

            """ create relationships between place and location node"""
            relationship_place_node = Relationship(place_node, "LOCATED_AT", location_node, created_at=date, updated_at=date)
            relationship_location_node = Relationship(location_node, "HAS_PLACE", place_node, created_at=date, updated_at=date)

            """ saving place and location node """
            secure_graph.create(place_node)
            secure_graph.create(location_node)
            """ saving place and location relationship """
            secure_graph.create(relationship_place_node)
            secure_graph.create(relationship_location_node)
            print("Successfully saved!......")
        else:
            print("{} already exist! skipping...".format(val["name"]))
            pass

    def saving_to_json_file(self, object_data):
        # initialize start time of execution
        start_time = time.time()

        # check file if exist, create if not
        if not os.path.isfile(self.filename):
            print("file dones not exist! creating file {}".format(self.filename))
            open(self.filename, "w+")

        # if file is greater than 50MB create another file
        # if os.path.getsize(self.filename)/(1024*1024.0) >= 50:
        #     Place(next_page_token=json.loads(res.decode())["next_page_token"],
        #           filename="results/" + str(datetime.datetime.now()).replace(" ", "-") + ".json")
        # else:
        # open file
        print("opening file: {}".format(self.filename))
        with open(self.filename, 'r') as fr:
            fread = fr.read()
            # check if there is a content inside the file
            if fread:
                # convert to json data
                data_read_json = json.loads(fread)
                # Writing JSON data
                with open(self.filename, 'w') as f:
                    # append data from request to existing data in the file
                    data_read_json.append(object_data)
                    """
                    save the new data ensure_ascii to false to also
                    save chinese, japanese, korean etc. languages context
                    """
                    json.dump(data_read_json, f, ensure_ascii=False)
            else:
                # write first data
                with open(self.filename, 'w') as f:
                    json.dump(self.__result["results"], f, ensure_ascii=False)

        """
        check the time execution per function call. if the time exceeds  15 seconds
        it means it's about getting and setting the data in the file so if true
        create another file for the new set of data
        """
        max_second_execution = 15
        if time.time() - start_time >= max_second_execution:  # in seconds
            self.set_file_directory_by_country(country=self.country)


class Command:
    @staticmethod
    def input_country():
        e_country = input("Enter a country: ").title()
        country_data = Place.find_country(name=e_country)

        if len(json.loads(country_data)["results"]) == 0:
            print("Country not found!\n")
            Command.input_country()
        else:
            return country_data

if __name__ == '__main__':

    secure_graph = Graph("http://neo4j:fullspeed@35.200.1.162:7474/db/data/")
    """timerecursionlimit is for opening , comparing, request execution adjustment
    """
    sys.setrecursionlimit(10000)
    place_api_key = "AIzaSyDrDTpAN4JDeaA94qBlD3--lCwS38cnMHQ"
    type_index = 0
    place_data = json.loads(Command.input_country())
    location = place_data["results"][0]["geometry"]["location"]
    Place(query=place_data["results"][0]["name"], country=place_data["results"][0]["name"],
          lat=location["lat"], lng=location["lng"])
    print("Google Place API Successfully generated!");