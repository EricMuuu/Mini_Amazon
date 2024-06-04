import socket
from google.protobuf.internal.decoder import _DecodeVarint32
from google.protobuf.internal.encoder import _EncodeVarint
import world_ups_pb2
import amazon_ups_pb2
# from ups_world import process_uwresponse
from ups_amazon import process_uaresponse, process_uwresponse

def create_client_socket(server_host, server_port):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        client_socket.connect((server_host, server_port))
        
        return client_socket
    except socket.error as e:
        print(f"Failed to connect: {e}")
        return None

def receive_protobuf(socket, message_class):
    data = b''
    while True:
        try:
            data += socket.recv(1)
            size = _DecodeVarint32(data, 0)[0]
            break
        except IndexError:
            pass
    data = socket.recv(size)
    # Now read the protobuf message itself
    # whole_message = socket.recv(msg_len)
    # Deserialize the data into the provided protobuf class
    message = message_class()
    message.ParseFromString(data)
    return message

def listen_world_socket(world_socket, db_pool, executor, amazon_socket):
    try:
        while True:
            message = receive_protobuf(world_socket, world_ups_pb2.UResponses)
            print(f"World message: \n{message}")
            # print(message)
            if message:
                executor.submit(process_uwresponse, message, db_pool, world_socket, amazon_socket)
            else:
                break
    finally:
        world_socket.close()

def listen_amazon_socket(amazon_socket, db_pool, executor, world_socket):
    try:
        while True:
            message = receive_protobuf(amazon_socket, amazon_ups_pb2.AUCommands)
            print(f"Amazon message: \n{message}")
            if message:
                executor.submit(process_uaresponse, message, db_pool, world_socket, amazon_socket)
            else:
                break
    finally:
        amazon_socket.close()

