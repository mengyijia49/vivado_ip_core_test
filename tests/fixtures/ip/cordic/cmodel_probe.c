#include <stdio.h>
#include "cordic_v6_0_bitacc_cmodel.h"

int main(void) {
    const unsigned values[] = {0, 1, 2, 3, 4, 6, 7, 8, 9, 255};
    const unsigned n = sizeof(values) / sizeof(values[0]);
    for (unsigned mode = 0; mode < 4; ++mode) {
        xip_cordic_v6_0_config config;
        if (xip_cordic_v6_0_default_config(&config)) return 1;
        config.name = "independent_diagnostic";
        config.CordicFunction = XIP_CORDIC_V6_0_F_SQRT;
        config.DataFormat = XIP_CORDIC_V6_0_FORMAT_USIG_INT;
        config.InputWidth = 8;
        config.OutputWidth = 5;
        config.CoarseRotate = 0;
        config.ScaleComp = 0;
        config.RoundMode = mode;
        config.Iterations = 0;
        config.Precision = 0;
        xip_cordic_v6_0 *core = xip_cordic_v6_0_create(&config, NULL, NULL);
        if (!core) return 2;
        xip_array_real *in = xip_array_real_create(), *out = xip_array_real_create();
        if (!in || !out) return 3;
        if (xip_array_real_reserve_data(in, n) || xip_array_real_reserve_dim(in, 1) ||
            xip_array_real_reserve_data(out, n) || xip_array_real_reserve_dim(out, 1)) return 4;
        in->dim_size = out->dim_size = 1;
        in->dim[0] = out->dim[0] = n;
        in->data_size = out->data_size = n;
        for (unsigned i = 0; i < n; ++i) in->data[i] = values[i];
        if (xip_cordic_v6_0_sqrt(core, in, out, n)) return 5;
        for (unsigned i = 0; i < n; ++i)
            printf("mode=%u input=%u output=%.17g\n", mode, values[i], out->data[i]);
        xip_array_real_destroy(in);
        xip_array_real_destroy(out);
        xip_cordic_v6_0_destroy(core);
    }
    return 0;
}
