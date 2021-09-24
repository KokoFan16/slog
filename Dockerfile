FROM ubuntu:latest
RUN apt-get update && apt-get install -y wget gnupg software-properties-common

RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key| apt-key add -
RUN add-apt-repository ppa:plt/racket
RUN apt-get update
RUN apt-get install -y clang-format clang-tidy clang-tools clang clangd libc++-dev libc++1 libc++abi-dev \
            libc++abi1 libclang-dev libclang1 liblldb-dev libllvm-ocaml-dev libomp-dev libomp5 lld lldb \ 
            llvm-dev llvm-runtime llvm python-clang mcpp cmake racket build-essential libopenmpi-dev openmpi-bin

RUN raco setup --doc-index --force-user-docs
RUN raco pkg install --batch --deps search-auto binaryio graph

RUN apt-get install -y git

# setup grpc
RUN git clone https://github.com/grpc/grpc /var/local/git/grpc --recurse-submodules && \
    cd /var/local/git/grpc && \
    git submodule update --init && \
    mkdir -p cmake/build && \
    cd cmake/build && \
    cmake ../.. && \
    make -j8 && make install

COPY . /slog

# build backend
RUN cd /slog/parallel-RA && CC=clang CXX=clang++ cmake -Bbuild .
RUN cd /slog/parallel-RA/build && CC=clang CXX=clang++ make -j8
WORKDIR /slog
# ENTRYPOINT [ "./slog-server" ]
