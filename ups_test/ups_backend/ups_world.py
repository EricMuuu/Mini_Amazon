from datetime import datetime
import psycopg2
from ups_amazon import send_UADelivered, send_UATruckArrived
import world_ups_pb2
from utils import seq_world, seq_amazon, send_protobuf

def process_uwresponse(message, db_pool, world_socket, amazon_socket):
    if message.completions:
        for completion in message.completions:
            send_world_ack(world_socket, completion.seqnum)
            process_completion(completion, db_pool, amazon_socket)

    if message.delivered:
        for delivery in message.delivered:
            send_world_ack(world_socket, delivery.seqnum)
            process_delivery(delivery, db_pool, amazon_socket)

    if message.acks:
        for ack in message.acks:
            # TO DO: handle ack
            seq_world.acknowledge(ack)
            print(f"Acknowledgement received for message {ack}.")

    if message.truckstatus:
        for truck in message.truckstatus:
            send_world_ack(world_socket, truck.seqnum)
            process_truckstatus(truck, db_pool)

    if message.error:
        for err in message.error:
            send_world_ack(world_socket, err.seqnum)
            print(f"Error: {err.err} in response to message {err.originseqnum}")
    
    if message.HasField("finished"):
        if message.finished == True:
            # TO DO: close connection
            return

def process_completion(completion, db_pool, amazon_socket):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE delivery_truck
                    SET x = %s, y = %s
                    WHERE truckId = %s
                    RETURNING status;
                """, (completion.x, completion.y, completion.truckid))
                current_status = cursor.fetchone()[0]

                cursor.execute("""
                        SELECT orderid, warehouseid, 
                        FROM delivery_order
                        WHERE truckid_id = %s;
                    """, (completion.truckid))
                order_status = cursor.fetchone()
                
                if current_status == 1:
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 1, loadTime = %s
                        WHERE truckId_id = %s AND status = 0;
                    """, (datetime.now(), completion.truckid))

                    cursor.execute("""
                        UPDATE delivery_truck
                        SET status = 2
                        WHERE truckId = %s;
                    """, (completion.truckid,))

                    conn.commit()
                    # TO DO: send_UATruckArrived()
                    seq_num = seq_world.next()
                    send_UATruckArrived(completion.truckid, order_status[0], order_status[1], seq_num, amazon_socket)
                    
                elif current_status == 3:
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 3, completeTime = %s
                        WHERE truckId_id = %s AND status = 2;
                    """, (datetime.now(), completion.truckid))

                    cursor.execute("""
                        UPDATE delivery_truck
                        SET status = 0
                        WHERE truckId = %s;
                    """, (completion.truckid,))
                    
                    conn.commit()
                    # TO DO: send_UADelivered()
                    seq_num = seq_amazon.next()
                    send_UADelivered(completion.truckid, order_status[0], seq_num, amazon_socket)

        except (Exception, psycopg2.DatabaseError) as e:
            print(f"Error in process_completion: {e}")
            conn.rollback()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_completion: {e}")

def process_delivery(delivered, db_pool, amazon_socket):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                update_order_stmt = """
                UPDATE delivery_order
                SET status = %s, completeTime = %s
                WHERE orderId = %s AND truckId_id = %s
                RETURNING orderid;
                """
                cursor.execute(update_order_stmt, (3, datetime.now(), delivered.packageid, delivered.truckid))
                order_id = cursor.fetchone()[0]
                conn.commit()
                
                # TO DO: send_UADelivered(delivered)
                seq_num = seq_amazon.next()
                send_UADelivered(delivered.truckid, order_id, seq_num, amazon_socket)

        except psycopg2.Error as e:
            conn.rollback() 
            print(f"Error in process_completion: {e}")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_delivered: {e}")

def process_truckstatus(truck, db_pool):
    try:
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cursor:
                update_truck_stmt = """
                UPDATE delivery_truck
                SET status = %s, x = %s, y = %s
                WHERE truckId = %s;
                """
                cursor.execute(update_truck_stmt, (truck.status, truck.x, truck.y, truck.truckid))
                conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error in process_truckstatus: {e}")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Get database connection failed in process_truckstatus: {e}")

def send_GoPickup(wh_id, truck_id, seq_num, world_socket, db_pool):
    try:
        message_gopick = world_ups_pb2.UGoPickup()
        message_gopick.truckid = truck_id
        message_gopick.whid = wh_id
        message_gopick.seq_num = seq_num

        message_command = world_ups_pb2.UCommands()
        message_command.pickups.add().CopyFrom(message_gopick)

        ack_event = seq_world.ack_events.get(seq_num)
        while ack_event and not ack_event.is_set():
        # send to the world
            send_protobuf(world_socket, message_command)
            print("sequence number = {}".format(seq_num))
            ack_event.wait(10)
            if ack_event.is_set():
                print("ACK received, stopping retransmissions.")
            else:
                print("ACK not received, timeout, resending...")
        # TO DO: accept ack

        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cursor:
                update_truck_stmt = """
                UPDATE delivery_truck
                SET status = %s
                WHERE truckId = %s;
                """
                cursor.execute(update_truck_stmt, (1, truck_id))
                cursor.commit()
        except psycopg2.Error as e:
            print(f"Error in send_GoPickup: {e}")
        finally:
            db_pool.put(conn)
    except Exception as e:
        print(f"Get database connection failed in send_GoPickup: {e}")

def send_GoDeliver(truck_id, seq_num, world_socket, db_pool):
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT orderId, destX, destY FROM delivery_order
                    WHERE truckId_id = %s AND status = 1;  # 假设status为1的订单是准备配送的订单
                """, (truck_id,))
                
                orders = cursor.fetchall()
                delivery_locations = []
                for order in orders:
                    order_id, dest_x, dest_y = order

                    delivery_location = world_ups_pb2.UDeliveryLocation()
                    delivery_location.packageid = order_id
                    delivery_location.x = dest_x
                    delivery_location.y = dest_y
                    delivery_locations.append(delivery_location)
                    
                    cursor.execute("""
                        UPDATE delivery_order
                        SET status = 2, deliverTime = %s
                        WHERE orderId = %s;
                    """, (datetime.now(), order_id))
        
                conn.commit()

                cursor.execute("""
                    UPDATE delivery_truck
                    SET status = 3
                    WHERE truckId = %s;
                """, (truck_id,))
                conn.commit()

            go_deliver = world_ups_pb2.UGoDeliver()
            go_deliver.truckid = truck_id
            go_deliver.seqnum = seq_num
            go_deliver.packages.extend(delivery_locations)

            ucommands = world_ups_pb2.UCommands()
            ucommands.deliveries.add().CopyFrom(go_deliver)

            # TO DO: accept acks
            ack_event = seq_world.ack_events.get(seq_num)
            while ack_event and not ack_event.is_set():
            # send to the world
                send_protobuf(world_socket, ucommands)
                print("sequence number = {}".format(seq_num))
                ack_event.wait(10)
                if ack_event.is_set():
                    print("ACK received, stopping retransmissions.")
                else:
                    print("ACK not received, timeout, resending...")

        except psycopg2.Error as e:
            print(f"Database error in send_GoDeliver: {e}")
            conn.rollback()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Error in send_GoDeliver: {e}")


def send_world_ack(socket, seq_num):
    ack_message = world_ups_pb2.UCommands()
    ack_message.acks.append(seq_num)
    send_protobuf(socket, ack_message)