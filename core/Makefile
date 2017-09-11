CXX_FLAGS=-O2 -Wall -std=c++11

all:
	g++ ${CXX_FLAGS} -shared -fPIC -fopenmp -o libocto.so octo.cpp -lhiredis
	g++ ${CXX_FLAGS} -o run run.cpp -locto

clean:
	rm libocto.so run
