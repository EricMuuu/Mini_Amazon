#include "proto_functions.hpp"
#include "world_amazon.pb.h"  
 
int main(int argc, char ** argv){
    int sockfd = createClient("23456");
    // AInitWarehouse warehouse;
    // warehouse.set_id(1);
    // warehouse.set_x(100);
    // warehouse.set_y(50);

    // google::protobuf::io::FileOutputStream fos(sockfd);
    // sendMesgTo(warehouse, &fos);

    // AInitWarehouse warehouse2;
    // google::protobuf::io::FileInputStream  fos2(sockfd);
    // recvMesgFrom(warehouse2, &fos2);
    // std::cout<<"Message received:\n"<<warehouse2.DebugString()<<endl;


    return EXIT_SUCCESS;
}