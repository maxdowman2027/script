/**
 * lut_phase0_fit.c — Force DPD LUT AM-PM through phase 0 (C reference).
 *
 * Algorithm matches dpd/lut_phase0_fit.py:
 *   1) amp = |I+jQ|, phase = unwrap(angle)
 *   2) Weighted LS poly fit vs LUT index with NO constant term
 *      → amp(0)=0, phase(0)=0
 *   3) Rebuild z = amp * exp(j*phase); force index0=(0,0), index1 Q=0
 *
 * Build (MSVC / MinGW / gcc)::
 *
 *   gcc -O2 -o lut_phase0_fit.exe dpd/lut_phase0_fit.c -lm
 *
 * Usage::
 *
 *   lut_phase0_fit.exe input.csv output.csv
 *   lut_phase0_fit.exe input.csv output.csv 4 4 2
 *
 * CSV format (header required)::
 *
 *   index,i,q
 *   0,0,0
 *   1,4096,0
 *   ...
 *
 * Optional args after paths: deg_amp deg_ph exclude_index
 *   (exclude_index < 0 means no exclude; default exclude=2)
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define LUT_PHASE0_MAX_N   64
#define LUT_PHASE0_MAX_DEG 8

typedef struct {
    int n;
    double i_in[LUT_PHASE0_MAX_N];
    double q_in[LUT_PHASE0_MAX_N];
    int i_out[LUT_PHASE0_MAX_N];
    int q_out[LUT_PHASE0_MAX_N];
    double amp_fit[LUT_PHASE0_MAX_N];
    double phase_fit[LUT_PHASE0_MAX_N];
    double coef_amp[LUT_PHASE0_MAX_DEG];
    double coef_ph[LUT_PHASE0_MAX_DEG];
    int deg_amp;
    int deg_ph;
    int exclude; /* single exclude index; <0 to disable */
} LutPhase0Fit;

static double lut_phase0_unwrap_step(double prev, double cur)
{
    double d = cur - prev;
    while (d > M_PI) {
        cur -= 2.0 * M_PI;
        d = cur - prev;
    }
    while (d < -M_PI) {
        cur += 2.0 * M_PI;
        d = cur - prev;
    }
    return cur;
}

static void lut_phase0_unwrap(const double *ph_in, double *ph_out, int n)
{
    int k;
    if (n <= 0) {
        return;
    }
    ph_out[0] = ph_in[0];
    for (k = 1; k < n; ++k) {
        ph_out[k] = lut_phase0_unwrap_step(ph_out[k - 1], ph_in[k]);
    }
}

/* Solve A x = b for square system (Gaussian elimination with partial pivot). */
static int lut_phase0_solve(double *A, double *b, double *x, int n)
{
    int i, j, k, piv;
    double maxv, tmp, fac;

    for (k = 0; k < n; ++k) {
        piv = k;
        maxv = fabs(A[k * n + k]);
        for (i = k + 1; i < n; ++i) {
            tmp = fabs(A[i * n + k]);
            if (tmp > maxv) {
                maxv = tmp;
                piv = i;
            }
        }
        if (maxv < 1e-18) {
            return -1;
        }
        if (piv != k) {
            for (j = k; j < n; ++j) {
                tmp = A[k * n + j];
                A[k * n + j] = A[piv * n + j];
                A[piv * n + j] = tmp;
            }
            tmp = b[k];
            b[k] = b[piv];
            b[piv] = tmp;
        }
        for (i = k + 1; i < n; ++i) {
            fac = A[i * n + k] / A[k * n + k];
            for (j = k; j < n; ++j) {
                A[i * n + j] -= fac * A[k * n + j];
            }
            b[i] -= fac * b[k];
        }
    }
    for (i = n - 1; i >= 0; --i) {
        tmp = b[i];
        for (j = i + 1; j < n; ++j) {
            tmp -= A[i * n + j] * x[j];
        }
        x[i] = tmp / A[i * n + i];
    }
    return 0;
}

/**
 * Weighted LS: y ≈ sum_{p=1..deg} c[p-1] * x^p
 * Normal equations via (X' W X) c = X' W y
 */
static int lut_phase0_poly_through_zero(
    const double *x,
    const double *y,
    const double *w,
    int n,
    int deg,
    double *coef_out)
{
    double AtWA[LUT_PHASE0_MAX_DEG * LUT_PHASE0_MAX_DEG];
    double AtWy[LUT_PHASE0_MAX_DEG];
    double Xp[LUT_PHASE0_MAX_DEG];
    int i, p, q;
    double wi, yp;

    if (deg < 1 || deg > LUT_PHASE0_MAX_DEG || n < deg) {
        return -1;
    }
    memset(AtWA, 0, sizeof(double) * (size_t)(deg * deg));
    memset(AtWy, 0, sizeof(double) * (size_t)deg);

    for (i = 0; i < n; ++i) {
        wi = (w != NULL) ? w[i] : 1.0;
        if (wi <= 0.0) {
            continue;
        }
        /* Xp[p] = x^(p+1) */
        Xp[0] = x[i];
        for (p = 1; p < deg; ++p) {
            Xp[p] = Xp[p - 1] * x[i];
        }
        yp = y[i];
        for (p = 0; p < deg; ++p) {
            AtWy[p] += wi * Xp[p] * yp;
            for (q = 0; q < deg; ++q) {
                AtWA[p * deg + q] += wi * Xp[p] * Xp[q];
            }
        }
    }
    return lut_phase0_solve(AtWA, AtWy, coef_out, deg);
}

static double lut_phase0_eval_through_zero(double x, const double *coef, int deg)
{
    double y = 0.0;
    double xp = x;
    int p;
    for (p = 0; p < deg; ++p) {
        y += coef[p] * xp;
        xp *= x;
    }
    return y;
}

static double lut_phase0_default_weight(int index, int early_bins, double early_w, double late_w)
{
    if (index < early_bins) {
        return early_w;
    }
    return late_w;
}

/**
 * Core API. On success returns 0 and fills fit->i_out / q_out.
 */
int lut_phase0_fit_run(LutPhase0Fit *fit)
{
    double amp[LUT_PHASE0_MAX_N];
    double ph_raw[LUT_PHASE0_MAX_N];
    double ph[LUT_PHASE0_MAX_N];
    double xf[LUT_PHASE0_MAX_N];
    double ampf[LUT_PHASE0_MAX_N];
    double phf[LUT_PHASE0_MAX_N];
    double wf[LUT_PHASE0_MAX_N];
    int n, k, m, rc;
    double zr, zi, a, p;

    if (fit == NULL) {
        return -1;
    }
    n = fit->n;
    if (n < 2 || n > LUT_PHASE0_MAX_N) {
        return -2;
    }
    if (fit->deg_amp < 1 || fit->deg_amp > LUT_PHASE0_MAX_DEG ||
        fit->deg_ph < 1 || fit->deg_ph > LUT_PHASE0_MAX_DEG) {
        return -3;
    }

    for (k = 0; k < n; ++k) {
        amp[k] = hypot(fit->i_in[k], fit->q_in[k]);
        ph_raw[k] = atan2(fit->q_in[k], fit->i_in[k]);
    }
    lut_phase0_unwrap(ph_raw, ph, n);

    m = 0;
    for (k = 0; k < n; ++k) {
        if (fit->exclude >= 0 && k == fit->exclude) {
            continue;
        }
        if (amp[k] <= 0.0) {
            continue;
        }
        xf[m] = (double)k;
        ampf[m] = amp[k];
        phf[m] = ph[k];
        wf[m] = lut_phase0_default_weight(k, 3, 1.0, 200.0);
        ++m;
    }
    if (m < fit->deg_amp || m < fit->deg_ph) {
        return -4;
    }

    rc = lut_phase0_poly_through_zero(xf, ampf, wf, m, fit->deg_amp, fit->coef_amp);
    if (rc != 0) {
        return -5;
    }
    rc = lut_phase0_poly_through_zero(xf, phf, wf, m, fit->deg_ph, fit->coef_ph);
    if (rc != 0) {
        return -6;
    }

    for (k = 0; k < n; ++k) {
        a = lut_phase0_eval_through_zero((double)k, fit->coef_amp, fit->deg_amp);
        p = lut_phase0_eval_through_zero((double)k, fit->coef_ph, fit->deg_ph);
        if (k == 0) {
            a = 0.0;
            p = 0.0;
        }
        fit->amp_fit[k] = a;
        fit->phase_fit[k] = p;
        zr = a * cos(p);
        zi = a * sin(p);
        if (k == 1) {
            /* force first non-zero bin onto real axis (phase 0) */
            zr = fabs(a);
            zi = 0.0;
        }
        fit->i_out[k] = (int)llround(zr);
        fit->q_out[k] = (int)llround(zi);
    }
    fit->i_out[0] = 0;
    fit->q_out[0] = 0;
    if (n > 1) {
        fit->q_out[1] = 0;
    }
    return 0;
}

static int lut_phase0_read_csv(const char *path, LutPhase0Fit *fit)
{
    FILE *fp;
    char line[256];
    int idx, ii, qq, n;

    fp = fopen(path, "r");
    if (fp == NULL) {
        perror(path);
        return -1;
    }
    /* skip header */
    if (fgets(line, sizeof(line), fp) == NULL) {
        fclose(fp);
        return -2;
    }
    n = 0;
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') {
            continue;
        }
        if (sscanf(line, "%d,%d,%d", &idx, &ii, &qq) != 3) {
            continue;
        }
        if (idx < 0 || idx >= LUT_PHASE0_MAX_N) {
            continue;
        }
        if (idx + 1 > n) {
            n = idx + 1;
        }
        fit->i_in[idx] = (double)ii;
        fit->q_in[idx] = (double)qq;
    }
    fclose(fp);
    fit->n = n;
    return (n > 0) ? 0 : -3;
}

static int lut_phase0_write_csv(const char *path, const LutPhase0Fit *fit)
{
    FILE *fp;
    int k;

    fp = fopen(path, "w");
    if (fp == NULL) {
        perror(path);
        return -1;
    }
    fprintf(fp, "index,i,q\n");
    for (k = 0; k < fit->n; ++k) {
        fprintf(fp, "%d,%d,%d\n", k, fit->i_out[k], fit->q_out[k]);
    }
    fclose(fp);
    return 0;
}

static int lut_phase0_write_map_txt(const char *path, const LutPhase0Fit *fit, int lut_sel)
{
    FILE *fp;
    int k;

    fp = fopen(path, "w");
    if (fp == NULL) {
        perror(path);
        return -1;
    }
    fprintf(fp, "# Optimized by lut_phase0_fit.c\n");
    fprintf(fp, "# phase forced through 0; deg_amp=%d deg_ph=%d exclude=%d\n",
            fit->deg_amp, fit->deg_ph, fit->exclude);
    fprintf(fp, "\nlut_data_map_lut%d = {\n", lut_sel);
    for (k = 0; k < fit->n; ++k) {
        fprintf(fp, "    %d: {\"i\": %d, \"q\": %d},\n",
                k, fit->i_out[k], fit->q_out[k]);
    }
    fprintf(fp, "}\n");
    fclose(fp);
    return 0;
}

int main(int argc, char **argv)
{
    LutPhase0Fit fit;
    char map_path[512];
    int rc;

    memset(&fit, 0, sizeof(fit));
    fit.deg_amp = 4;
    fit.deg_ph = 4;
    fit.exclude = 2;

    if (argc < 3) {
        fprintf(stderr,
                "Usage: %s input.csv output.csv [deg_amp deg_ph exclude]\n"
                "  exclude < 0 disables outlier drop (default exclude=2)\n",
                argv[0]);
        return 1;
    }
    if (argc >= 4) {
        fit.deg_amp = atoi(argv[3]);
    }
    if (argc >= 5) {
        fit.deg_ph = atoi(argv[4]);
    }
    if (argc >= 6) {
        fit.exclude = atoi(argv[5]);
    }

    rc = lut_phase0_read_csv(argv[1], &fit);
    if (rc != 0) {
        fprintf(stderr, "read csv failed (%d)\n", rc);
        return 2;
    }
    rc = lut_phase0_fit_run(&fit);
    if (rc != 0) {
        fprintf(stderr, "fit failed (%d)\n", rc);
        return 3;
    }
    rc = lut_phase0_write_csv(argv[2], &fit);
    if (rc != 0) {
        return 4;
    }
    snprintf(map_path, sizeof(map_path), "%s", argv[2]);
    {
        /* write sibling .txt map if output ends with .csv */
        size_t L = strlen(map_path);
        if (L > 4 && strcmp(map_path + L - 4, ".csv") == 0) {
            memcpy(map_path + L - 4, ".txt", 4);
        } else {
            strncat(map_path, ".txt", sizeof(map_path) - strlen(map_path) - 1);
        }
    }
    lut_phase0_write_map_txt(map_path, &fit, 0);

    printf("[OK] n=%d deg_amp=%d deg_ph=%d exclude=%d\n",
           fit.n, fit.deg_amp, fit.deg_ph, fit.exclude);
    printf("[OK] csv → %s\n", argv[2]);
    printf("[OK] map → %s\n", map_path);
    printf("[OK] out[0]=(%d,%d) out[1]=(%d,%d)\n",
           fit.i_out[0], fit.q_out[0], fit.i_out[1], fit.q_out[1]);
    return 0;
}
