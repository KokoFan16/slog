/*
 * copy
 * Copyright (c) Ke Fan
 */


#pragma once
#include "../ds.h"

class parallel_copy_aggregate: public parallel_RA
{

private:

    relation* agg_input0_table;
    relation* agg_input1_table;
    int agg_input1_graph_type;
    relation* agg_output_table;

public:

    parallel_copy_aggregate()
    {
        RA_type = AGGREGATE;
    }

    parallel_copy_aggregate(relation* output, relation* agg_rel, relation* target_rel, int rel_type, int agg_op)
    : agg_input0_table(agg_rel), agg_input1_table(target_rel), agg_input1_graph_type(rel_type), agg_output_table(output)
    {
    		RA_type = AGGREGATE;
    }

//    parallel_copy_aggregate(relation* output, relation* agg_rel, relation* target_rel, int rel_type, local_agg_func_t local_agg_func, int aggregate_type, global_agg_func_t global_agg_fun);

    relation* get_agg_input0() {return agg_input0_table;}
    relation* get_agg_input1() {return agg_input1_table;}
    int get_agg_input1_graph_type() {return agg_input1_graph_type;}
    relation* get_agg_output() {return agg_output_table;}

    bool local_aggregate(
    		u32 buckets,
    		shmap_relation* input0,
    		shmap_relation* input1,
    		relation* output);

};
