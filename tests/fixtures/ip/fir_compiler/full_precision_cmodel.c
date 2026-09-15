#include <stdio.h>
#include <stdlib.h>

#include "fir_compiler_v7_2_bitacc_cmodel.h"

static const double coefficients[3][3] = {{-8, 0, 0}, {-1, -1, -2}, {1, 1, 2}};
static const double inputs[16] = {0, -128, -128, -128, 127, -127, 0, 1, -1, 64, -64, 0, 0, 0, 0, 0};
static const double expected[3][16] = {
    {0, 1024, 1024, 1024, -1016, 1016, 0, -8, 8, -512, 512, 0, 0, 0, 0, 0},
    {0, 128, 256, 512, 257, 256, -127, 253, 0, -65, 2, -64, 128, 0, 0, 0},
    {0, -128, -256, -512, -257, -256, 127, -253, 0, 65, -2, 64, -128, 0, 0, 0}
};

static void check(xip_status status, const char *operation) {
    if (status != XIP_STATUS_OK) {
        fprintf(stderr, "FIR_CMODEL_ERROR: %s\n", operation);
        exit(2);
    }
}

static void message(void *handle, int error, const char *text) {
    (void)handle;
    fprintf(stderr, "FIR_CMODEL_MESSAGE %d: %s\n", error, text);
}

static unsigned probe(unsigned kind, unsigned width) {
    xip_fir_v7_2_config config, actual_config;
    check(xip_fir_v7_2_default_config(&config), "default config");
    config.name = "fir_full_precision_probe";
    config.data_coefficient_type = XIP_FIR_REAL_TYPE;
    config.filter_type = XIP_FIR_SINGLE_RATE;
    config.rate_change = XIP_FIR_INTEGER_RATE;
    config.interp_rate = 1;
    config.decim_rate = 1;
    config.zero_pack_factor = 1;
    config.accum_width = width;
    config.coeff = coefficients[kind];
    config.coeff_padding = 0;
    config.num_coeffs = 3;
    config.coeff_sets = 1;
    config.reloadable = 0;
    config.is_halfband = 0;
    config.quantization = XIP_FIR_INTEGER_COEFF;
    config.coeff_width = 4;
    config.coeff_fract_width = 0;
    config.chan_seq = XIP_FIR_BASIC_CHAN_SEQ;
    config.num_channels = 1;
    config.num_paths = 1;
    config.data_width = 8;
    config.data_fract_width = 0;
    config.output_rounding_mode = XIP_FIR_FULL_PRECISION;
    config.output_width = 0;
    config.config_method = XIP_FIR_CONFIG_SINGLE;
    xip_fir_v7_2 *model = xip_fir_v7_2_create(&config, message, NULL);
    if (!model) {
        fprintf(stderr, "FIR_CMODEL_ERROR: create\n");
        exit(2);
    }
    check(xip_fir_v7_2_get_config(model, &actual_config), "get config");
    printf("FIR_CMODEL_CONFIG %u requested_accum=%u accum=%u output=%u fraction=%u\n",
           kind, width, actual_config.accum_width, actual_config.output_width, actual_config.output_fract_width);
    xip_array_real *source = xip_array_real_create();
    xip_array_real *sink = xip_array_real_create();
    if (!source || !sink) {
        fprintf(stderr, "FIR_CMODEL_ERROR: allocate arrays\n");
        exit(2);
    }
    check(xip_array_real_reserve_dim(source, 3), "reserve dimensions");
    source->dim_size = 3;
    source->dim[0] = 1;
    source->dim[1] = 1;
    source->dim[2] = 16;
    check(xip_array_real_reserve_data(source, 16), "reserve data");
    source->data_size = 16;
    for (unsigned i = 0; i < 16; ++i) source->data[i] = inputs[i];
    check(xip_fir_v7_2_reset(model), "reset");
    check(xip_fir_v7_2_set_data_sink(model, sink, NULL), "set data sink");
    check(xip_fir_v7_2_data_send(model, source), "send data");
    if (sink->data_size != 16 || sink->dim_size != 3 || sink->dim[0] != 1 ||
        sink->dim[1] != 1 || sink->dim[2] != 16) {
        fprintf(stderr, "FIR_CMODEL_ERROR: output shape\n");
        exit(2);
    }
    unsigned failures = 0;
    for (unsigned i = 0; i < 16; ++i) {
        printf("FIR_CMODEL_SAMPLE %u width=%u index=%u expected=%.17g actual=%.17g\n",
               kind, width, i, expected[kind][i], sink->data[i]);
        failures += sink->data[i] != expected[kind][i];
    }
    check(xip_fir_v7_2_destroy(model), "destroy");
    xip_array_real_destroy(source);
    xip_array_real_destroy(sink);
    return failures;
}

int main(void) {
    const unsigned sufficient_widths[3] = {12, 11, 10};
    unsigned failures = 0;
    printf("FIR_CMODEL_VERSION %s\n", xip_fir_v7_2_get_version());
    for (unsigned kind = 0; kind < 3; ++kind) {
        failures += probe(kind, XIP_FIR_CALC_ACCUM_WIDTH);
        failures += probe(kind, sufficient_widths[kind]);
    }
    printf("FIR_CMODEL_STATUS: %s differences=%u\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
