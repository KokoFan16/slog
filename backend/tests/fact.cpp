#include "../src/parallel_RA_inc.h"

// builtins.cpp goes here!
// builtins.cpp
#include <vector>
#include <string>
#include <cassert>
#include <iostream>
#include <array>
#include <functional>
#include <tuple>

using namespace std;
#define u64  unsigned long long
using i64 = long long;

const u64 tag_mask = 0xffffc00000000000;
const u64 tag_position = 46;
const u64 int_tag = 0;

inline bool is_number(u64 datum) {
  // cout << "is_number(" << datum << "): " << (datum >> tag_position == int_tag) << "\n";
  return datum >> tag_position == int_tag;
}

inline i64 datum_to_number(u64 datum) {
  return (i64) (datum & ~tag_mask) << (64 - tag_position) >> (64 - tag_position);
}
const auto d2n = datum_to_number;

inline u64 number_to_datum(i64 number) {
  return (number & ~tag_mask) | (int_tag << tag_position);
}
const auto n2d = number_to_datum;




vector<array<u64,2>> builtin_div_rem(const u64* const data){
  if (is_number(data[0]) && is_number(data[1])){
    auto div = number_to_datum(d2n(data[0]) / d2n(data[1]));
    auto rem = number_to_datum(d2n(data[0]) % d2n(data[1]));
    return {{div, rem}};
  } else {
    return {};
  }
}

#define BUILTIN_BINARY_NUMBER_PRED(name, op) \
template<typename TState> inline TState name(const u64* data, TState init_state, TState (*callback) (TState state)){ \
  if (is_number(data[0]) && is_number(data[1]) &&\
      datum_to_number(data[0]) op datum_to_number(data[1])){\
    return callback(init_state);\
  } else \
    return init_state;\
}

BUILTIN_BINARY_NUMBER_PRED(builtin_less, <)
BUILTIN_BINARY_NUMBER_PRED(builtin_greater, >)
BUILTIN_BINARY_NUMBER_PRED(builtin_le, <=)
BUILTIN_BINARY_NUMBER_PRED(builtin_ge, >=)

#define BUILTIN_BINARY_NUMBER_FUNC(name, op) \
template<typename TState> inline TState name(const u64* data, TState init_state, TState (*callback) (u64 res, TState state)){ \
  if (is_number(data[0]) && is_number(data[1])){\
    auto res = number_to_datum(datum_to_number(data[0]) op datum_to_number(data[1]));\
    return callback(res, init_state);\
} else \
  return init_state;\
}

BUILTIN_BINARY_NUMBER_FUNC(builtin_add, +)
BUILTIN_BINARY_NUMBER_FUNC(builtin_subtract, -)
BUILTIN_BINARY_NUMBER_FUNC(builtin_multiply, *)
BUILTIN_BINARY_NUMBER_FUNC(builtin_divide, /)


#define BUILTIN_UNARY_NUMBER_FUNC(name, impl) \
template<typename TState> inline TState name(const u64* data, TState init_state, TState (*callback) (u64 res, TState state)){ \
  if (is_number(data[0])){\
    auto res = number_to_datum(impl(datum_to_number(data[0])));\
    return callback(res, init_state);\
} else \
  return init_state;\
}

inline u64 add1(u64 x) {return x + 1;}
inline u64 sub1(u64 x) {return x - 1;}

BUILTIN_UNARY_NUMBER_FUNC(builtin_add1, add1)
BUILTIN_UNARY_NUMBER_FUNC(builtin_add1_2, sub1)
BUILTIN_UNARY_NUMBER_FUNC(builtin_sub1, sub1)
BUILTIN_UNARY_NUMBER_FUNC(builtin_sub1_2, add1)


vector<array<u64,1>> builtin_range(const u64* const data){
  vector<array<u64,1>> res;
  if (is_number(data[0]) && is_number(data[1])){
    auto lb = datum_to_number(data[0]);
    auto ub = datum_to_number(data[1]);
    res.reserve(ub - lb);
    for (u64 x = lb; x < ub; x++)
      res.push_back({number_to_datum(x)});
  }
  return res;
}

template<typename TState>
TState callback_builtin_range(const u64* data, TState init_state, TState (*callback) (u64 res, TState state)){
  auto state = init_state;
  if (is_number(data[0]) && is_number(data[1])){
    auto lb = datum_to_number(data[0]);
    auto ub = datum_to_number(data[1]);
    for (u64 x = lb; x < ub; x++)
      state = callback(number_to_datum(x), state);
  }
  return state;
}


#define BUILTIN_BINARY_PRED(name, op) \
template<typename TState> TState name(const u64* data, TState init_state, TState (*callback) (TState state)){ \
  if (data[0] op data[1])\
    return callback(init_state);\
  else\
    return init_state;\
}
BUILTIN_BINARY_PRED(builtin_eq, ==)
BUILTIN_BINARY_PRED(builtin_neq, !=)

template<typename TState>
TState builtin_eq_1(const u64* data, TState init_state, TState (*callback) (u64 res, TState state)){
  return callback(data[0], init_state);
}

#define BUILTIN_UNARY_PRED(name, pred) \
template<typename TState> TState name(const u64* data, TState init_state, TState (*callback) (TState state)){ \
  if (pred(data[0]))\
    return callback(init_state);\
  else\
    return init_state;\
}

bool is_not_number(u64 datum) {return !is_number(datum);}
BUILTIN_UNARY_PRED(builtin_number_huh, is_number)
BUILTIN_UNARY_PRED(builtin_not_number_huh, is_not_number)

// for generate-cpp-lambda-for-computational-join
struct CL2CB_State{
  void* original_callback; // There be dragons?
  void* original_state;
  const u64* original_data;
  u64* cl1_output_args;
};

// for generate-cpp-lambda-for-computational-copy
struct BCLCB_State{
  void* original_callback;
  void* original_state;
  const u64* original_data;
};

//an experiment:
template<bool f (u64, u64)>
bool builtin_binary_number_pred(const u64* data){
  if (is_number(data[0]) && is_number(data[1])){
    return f(datum_to_number(data[0]), datum_to_number(data[1]));
  } else {
    return false;
  }
}
bool _less(u64 x, u64 y) { return x < y;}
auto builtin_less2 = builtin_binary_number_pred<_less>;

// end of builtins.cpp


// global definitions:


int main(int argc, char **argv)
{
  mpi_comm mcomm;
  mcomm.create(argc, argv);

relation* rel__unit__0__ = new relation(0, true, 0, 258, "rel__unit__0__", "../data/fact//unit_0_3.dat", FULL);
relation* rel__foo__1__ = new relation(0, false, 1, 257, "rel__foo__1__", "../data/fact//foo_1_2.dat", FULL);
relation* rel__foo__1__1 = new relation(1, true, 1, 257, "rel__foo__1__1", "../data/fact//foo_1_1.dat", FULL);
relation* rel__bar__1__1 = new relation(1, true, 1, 256, "rel__bar__1__1", "../data/fact//bar_1_0.dat", FULL);

RAM* scc6550 = new RAM(false, 1);
scc6550->add_relation(rel__unit__0__, true);
scc6550->add_rule(new fact(rel__unit__0__, {}));

RAM* scc6551 = new RAM(false, 3);
scc6551->add_relation(rel__foo__1__1, true);
std::cout << "Test " << n2d(1) << std::endl;
scc6551->add_rule(new fact(rel__foo__1__1, {n2d(1)}));

RAM* scc6552 = new RAM(false, 0);
scc6552->add_relation(rel__foo__1__1, true);
scc6552->add_relation(rel__foo__1__, true);
scc6552->add_rule(new parallel_acopy(rel__foo__1__, rel__foo__1__1, DELTA, {1, 0}));

RAM* scc6553 = new RAM(false, 2);
scc6553->add_relation(rel__bar__1__1, true);
scc6553->add_rule(new parallel_copy(rel__bar__1__1, rel__foo__1__1, FULL, {0}));

LIE* lie = new LIE();
lie->add_relation(rel__unit__0__);
lie->add_relation(rel__foo__1__);
lie->add_relation(rel__foo__1__1);
lie->add_relation(rel__bar__1__1);
lie->add_scc(scc6550);
lie->add_scc(scc6551);
lie->add_scc(scc6552);
lie->add_scc(scc6553);
lie->add_scc_dependance(scc6551, scc6553);
lie->add_scc_dependance(scc6551, scc6552);



  // Enable IO
 lie->enable_share_io();
 lie->set_output_dir("../data/fact-output"); // Write to this directory
 lie->set_comm(mcomm);
 lie->set_batch_size(1);
 lie->execute();
 lie->print_all_relation_size(); // Continuously print relation sizes

 delete lie;
 mcomm.destroy();
 return 0;
}
