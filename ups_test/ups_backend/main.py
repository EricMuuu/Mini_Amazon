import world_ups_pb2
import amazon_ups_pb2
from utils import *
from server import create_client_socket, receive_protobuf, listen_amazon_socket, listen_world_socket
import threading
from concurrent.futures import ThreadPoolExecutor


idle_trucks = []
busy_trucks = []

if __name__ == "__main__":

    # Create Database connection pool
    dbconnection_pool = create_dbconnection_pool()

    # init database
    init_database(dbconnection_pool)

    # Establish connection with worldSim
    server_host = "127.0.0.1"
    server_port = 12345
    world_socket = create_client_socket(server_host, server_port)

    # Send UConnect message
    uwconnect_message = init_UConnect(dbconnection_pool)
    send_protobuf(world_socket, uwconnect_message)
    # Recieve UConnected message
    uwconnect_response = receive_protobuf(world_socket, world_ups_pb2.UConnected)
    print(uwconnect_response)

    # Establish connection with Amazon
    # amazon_host = "vcm-37900.vm.duke.edu"
    amazon_port = 9999
    amazon_host = "67.159.95.216"
    # amazon_port = 9999
    amazon_socket = create_client_socket(amazon_host, amazon_port)

    # Send UAConnect message
    uaconnect_message = init_UAConnect(uwconnect_response.worldid)
    send_protobuf(amazon_socket, uaconnect_message)
    # Recieve UAConfirmConnect
    uaconnect_response = receive_protobuf(amazon_socket, amazon_ups_pb2.AUConfirmConnect)
    print(uaconnect_response)

    # do stuff
    with ThreadPoolExecutor(max_workers=20) as executor:
        world_thread = threading.Thread(target=listen_world_socket, args=(world_socket, dbconnection_pool, executor, amazon_socket))
        amazon_thread = threading.Thread(target=listen_amazon_socket, args=(amazon_socket, dbconnection_pool, executor, world_socket))

        world_thread.start()
        amazon_thread.start()

        world_thread.join()
        amazon_thread.join()


