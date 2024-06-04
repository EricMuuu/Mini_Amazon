# Compiler and flags
CXX = g++
CXXFLAGS = -Wall -std=c++11 -g
PROTOC = protoc
PROTO_FLAGS = --cpp_out=.

# Source files
PROTO_SRC = world_amazon.proto
PROTO_GEN = world_amazon.pb.h #world_amazon.pb.cc
CPP_SRC = $(wildcard *.cpp)
CPP_OBJ = $(CPP_SRC:.cpp=.o)

# Executable name
EXEC = program

# Default rule
all: $(EXEC)

# Rule for generating .pb.cc and .pb.h from .proto
%.pb.cc %.pb.h: %.proto
	$(PROTOC) $(PROTO_FLAGS) $<

# Rule for object files
%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Rule for executable
$(EXEC): $(PROTO_GEN) $(CPP_OBJ)
	$(CXX) $(CXXFLAGS) $^ -o $@ -lprotobuf

# Clean rule
clean:
	rm -f $(CPP_OBJ) $(PROTO_GEN) $(EXEC)

.PHONY: all clean
