/**
 * lut_phase0_fit.c — Chip-friendly DPD LUT phase-through-0 smooth (C).
 *
 * Methods (match dpd/lut_phase0_fit.py):
 *   ma   — moving average on amp/phase  [DEFAULT, O(N*W), for on-chip SW]
 *   poly — weighted no-constant poly LS [optional / offline]
 *
 * Bad bins (match Python):
 *   exclude mode AUTO (default): detect amp dip/spike vs neighbor mean,
 *   then interpolate. No hard-coded index=2 required for chip automation.
 *   exclude < 0 and != AUTO disables; exclude >= 0 forces that single index.
 *
 * Build::
 *   gcc -O2 -o lut_phase0_fit.exe dpd/lut_phase0_fit.c -lm
 *
 * Usage::
 *   lut_phase0_fit.exe in.csv out.csv
 *   lut_phase0_fit.exe in.csv out.csv ma 5
 *   lut_phase0_fit.exe in.csv out.csv ma 5 auto
 *   lut_phase0_fit.exe in.csv out.csv ma 5 none
 *   lut_phase0_fit.exe in.csv out.csv ma 5 2
 *   lut_phase0_fit.exe in.csv out.csv poly 4 4 auto
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
#define LUT_PHASE0_MAX_WIN 31

/* exclude modes: match Python resolve_exclude / detect_lut_outliers */
#define LUT_PHASE0_EXCLUDE_AUTO  (-2)
#define LUT_PHASE0_EXCLUDE_NONE  (-1)

/* Auto outlier thresholds (must match lut_phase0_fit.py) */
#define LUT_PHASE0_AUTO_AMP_NEIGH_MIN   200.0
#define LUT_PHASE0_AUTO_AMP_REL_THR     0.40
#define LUT_PHASE0_AUTO_AMP_DIP_FACTOR  0.60
#define LUT_PHASE0_AUTO_AMP_SPIKE_FACTOR 1.80
#define LUT_PHASE0_AUTO_PHASE_THR_RAD   (40.0 * M_PI / 180.0)
#define LUT_PHASE0_AUTO_AMP_MIN_FOR_PHASE 300.0
#define LUT_PHASE0_AUTO_PHASE_REL_THR   0.25

typedef enum {
    LUT_METHOD_MA = 0,
    LUT_METHOD_POLY = 1
} LutPhase0Method;

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
    LutPhase0Method method;
    int deg_amp;
    int deg_ph;
    int ma_win;
    int exclude;          /* AUTO / NONE / single manual index */
    int exclude_mask[LUT_PHASE0_MAX_N]; /* filled by fit_run */
    int force_index1_real;
    int is_master;        /* if 0 and amp[1] tiny, skip force I1 */
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

static void lut_phase0_detect_outliers(const double *amp, const double *ph, int n, int *mask)
{
    int k;
    double a_l, a_c, a_r, pred, rel, ph_err;
    int is_dip, is_spike, is_ph;

    memset(mask, 0, sizeof(int) * (size_t)n);
    for (k = 1; k < n - 1; ++k) {
        a_l = amp[k - 1];
        a_c = amp[k];
        a_r = amp[k + 1];
        if (a_l < LUT_PHASE0_AUTO_AMP_NEIGH_MIN || a_r < LUT_PHASE0_AUTO_AMP_NEIGH_MIN) {
            continue;
        }
        pred = 0.5 * (a_l + a_r);
        rel = fabs(a_c - pred) / ((pred > 1.0) ? pred : 1.0);
        is_dip = (a_c < LUT_PHASE0_AUTO_AMP_DIP_FACTOR * ((a_l < a_r) ? a_l : a_r)) ? 1 : 0;
        is_spike = (a_c > LUT_PHASE0_AUTO_AMP_SPIKE_FACTOR * ((a_l > a_r) ? a_l : a_r)) ? 1 : 0;
        ph_err = fabs(ph[k] - 0.5 * (ph[k - 1] + ph[k + 1]));
        is_ph = (ph_err > LUT_PHASE0_AUTO_PHASE_THR_RAD && pred >= LUT_PHASE0_AUTO_AMP_MIN_FOR_PHASE) ? 1 : 0;
        if ((is_dip || is_spike) && rel >= LUT_PHASE0_AUTO_AMP_REL_THR) {
            mask[k] = 1;
        } else if (is_ph && rel >= LUT_PHASE0_AUTO_PHASE_REL_THR && (is_dip || is_spike)) {
            mask[k] = 1;
        }
    }
}

/* Linear interp of masked bins from remaining good samples (O(N)). */
static void lut_phase0_interp_mask(double *y, int n, const int *mask)
{
    int k, a, b;
    double t;
    for (k = 0; k < n; ++k) {
        if (!mask[k]) {
            continue;
        }
        a = k - 1;
        while (a >= 0 && mask[a]) {
            --a;
        }
        b = k + 1;
        while (b < n && mask[b]) {
            ++b;
        }
        if (a < 0 && b >= n) {
            y[k] = 0.0;
        } else if (a < 0) {
            y[k] = y[b];
        } else if (b >= n) {
            y[k] = y[a];
        } else {
            t = (double)(k - a) / (double)(b - a);
            y[k] = y[a] * (1.0 - t) + y[b] * t;
        }
    }
}

static void lut_phase0_build_exclude_mask(LutPhase0Fit *fit, const double *amp, const double *ph)
{
    int k;
    memset(fit->exclude_mask, 0, sizeof(fit->exclude_mask));
    if (fit->exclude == LUT_PHASE0_EXCLUDE_NONE) {
        return;
    }
    if (fit->exclude == LUT_PHASE0_EXCLUDE_AUTO) {
        lut_phase0_detect_outliers(amp, ph, fit->n, fit->exclude_mask);
        return;
    }
    /* manual single index */
    k = fit->exclude;
    if (k >= 0 && k < fit->n) {
        fit->exclude_mask[k] = 1;
    }
}

/* Centered MA, odd win, edge replicate — chip O(N*W). */
static void lut_phase0_moving_average(const double *in, double *out, int n, int win)
{
    int k, j, half;
    double sum;
    if (win < 3) {
        memcpy(out, in, sizeof(double) * (size_t)n);
        return;
    }
    if ((win & 1) == 0) {
        ++win;
    }
    if (win > LUT_PHASE0_MAX_WIN) {
        win = LUT_PHASE0_MAX_WIN | 1;
    }
    half = win / 2;
    for (k = 0; k < n; ++k) {
        sum = 0.0;
        for (j = -half; j <= half; ++j) {
            int idx = k + j;
            if (idx < 0) {
                idx = 0;
            }
            if (idx >= n) {
                idx = n - 1;
            }
            sum += in[idx];
        }
        out[k] = sum / (double)win;
    }
}

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

static int lut_phase0_poly_through_zero(
    const double *x, const double *y, const double *w, int n, int deg, double *coef_out)
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
    double y = 0.0, xp = x;
    int p;
    for (p = 0; p < deg; ++p) {
        y += coef[p] * xp;
        xp *= x;
    }
    return y;
}

static double lut_phase0_default_weight(int index)
{
    return (index < 3) ? 1.0 : 200.0;
}

int lut_phase0_fit_run(LutPhase0Fit *fit)
{
    double amp[LUT_PHASE0_MAX_N];
    double ph_raw[LUT_PHASE0_MAX_N];
    double ph[LUT_PHASE0_MAX_N];
    double amp_w[LUT_PHASE0_MAX_N];
    double ph_w[LUT_PHASE0_MAX_N];
    double xf[LUT_PHASE0_MAX_N];
    double ampf[LUT_PHASE0_MAX_N];
    double phf[LUT_PHASE0_MAX_N];
    double wf[LUT_PHASE0_MAX_N];
    int n, k, m, rc;
    double a, p, zr, zi, ph0;

    if (fit == NULL) {
        return -1;
    }
    n = fit->n;
    if (n < 2 || n > LUT_PHASE0_MAX_N) {
        return -2;
    }

    for (k = 0; k < n; ++k) {
        amp[k] = hypot(fit->i_in[k], fit->q_in[k]);
        ph_raw[k] = atan2(fit->q_in[k], fit->i_in[k]);
    }
    lut_phase0_unwrap(ph_raw, ph, n);
    memcpy(amp_w, amp, sizeof(double) * (size_t)n);
    memcpy(ph_w, ph, sizeof(double) * (size_t)n);
    lut_phase0_build_exclude_mask(fit, amp, ph);
    lut_phase0_interp_mask(amp_w, n, fit->exclude_mask);
    lut_phase0_interp_mask(ph_w, n, fit->exclude_mask);

    if (fit->method == LUT_METHOD_MA) {
        lut_phase0_moving_average(amp_w, fit->amp_fit, n, fit->ma_win);
        lut_phase0_moving_average(ph_w, fit->phase_fit, n, fit->ma_win);
    } else {
        m = 0;
        for (k = 0; k < n; ++k) {
            if (fit->exclude_mask[k]) {
                continue;
            }
            if (amp[k] <= 0.0) {
                continue;
            }
            xf[m] = (double)k;
            ampf[m] = amp[k];
            phf[m] = ph[k];
            wf[m] = lut_phase0_default_weight(k);
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
            fit->amp_fit[k] = lut_phase0_eval_through_zero((double)k, fit->coef_amp, fit->deg_amp);
            fit->phase_fit[k] = lut_phase0_eval_through_zero((double)k, fit->coef_ph, fit->deg_ph);
        }
    }

    /* Force through 0 */
    ph0 = fit->phase_fit[0];
    for (k = 0; k < n; ++k) {
        if (fit->amp_fit[k] < 0.0) {
            fit->amp_fit[k] = 0.0;
        }
        fit->phase_fit[k] -= ph0;
    }
    fit->amp_fit[0] = 0.0;
    fit->phase_fit[0] = 0.0;

    for (k = 0; k < n; ++k) {
        a = fit->amp_fit[k];
        p = fit->phase_fit[k];
        if (a < 1.0) {
            fit->i_out[k] = 0;
            fit->q_out[k] = 0;
            continue;
        }
        zr = a * cos(p);
        zi = a * sin(p);
        if (k == 1 && fit->force_index1_real && fit->is_master) {
            zr = fabs(a);
            zi = 0.0;
        }
        fit->i_out[k] = (int)llround(zr);
        fit->q_out[k] = (int)llround(zi);
    }
    fit->i_out[0] = 0;
    fit->q_out[0] = 0;
    if (n > 1 && fit->force_index1_real && fit->is_master && fit->amp_fit[1] >= 1.0) {
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
    const char *emode;
    fp = fopen(path, "w");
    if (fp == NULL) {
        perror(path);
        return -1;
    }
    if (fit->exclude == LUT_PHASE0_EXCLUDE_AUTO) {
        emode = "auto";
    } else if (fit->exclude == LUT_PHASE0_EXCLUDE_NONE) {
        emode = "none";
    } else {
        emode = "manual";
    }
    fprintf(fp, "# Optimized by lut_phase0_fit.c method=%s\n",
            (fit->method == LUT_METHOD_MA) ? "ma" : "poly");
    fprintf(fp, "# phase through 0; ma_win=%d deg_amp=%d deg_ph=%d exclude_mode=%s master=%d\n",
            fit->ma_win, fit->deg_amp, fit->deg_ph, emode, fit->is_master);
    fprintf(fp, "# exclude_mask=");
    for (k = 0; k < fit->n; ++k) {
        if (fit->exclude_mask[k]) {
            fprintf(fp, "%d ", k);
        }
    }
    fprintf(fp, "\n");
    fprintf(fp, "\nlut_data_map_lut%d = {\n", lut_sel);
    for (k = 0; k < fit->n; ++k) {
        fprintf(fp, "    %d: {\"i\": %d, \"q\": %d},\n", k, fit->i_out[k], fit->q_out[k]);
    }
    fprintf(fp, "}\n");
    fclose(fp);
    return 0;
}

static int lut_phase0_parse_exclude_arg(const char *s)
{
    if (s == NULL || s[0] == '\0') {
        return LUT_PHASE0_EXCLUDE_AUTO;
    }
    if (strcmp(s, "auto") == 0 || strcmp(s, "detect") == 0) {
        return LUT_PHASE0_EXCLUDE_AUTO;
    }
    if (strcmp(s, "none") == 0 || strcmp(s, "off") == 0 || strcmp(s, "disable") == 0) {
        return LUT_PHASE0_EXCLUDE_NONE;
    }
    return atoi(s);
}

int main(int argc, char **argv)
{
    LutPhase0Fit fit;
    char map_path[512];
    int rc, k;
    size_t L;

    memset(&fit, 0, sizeof(fit));
    fit.method = LUT_METHOD_MA;
    fit.ma_win = 5;
    fit.deg_amp = 4;
    fit.deg_ph = 4;
    fit.exclude = LUT_PHASE0_EXCLUDE_AUTO;
    fit.force_index1_real = 1;
    fit.is_master = 1;

    if (argc < 3) {
        fprintf(stderr,
                "Usage:\n"
                "  %s in.csv out.csv\n"
                "  %s in.csv out.csv ma [ma_win] [exclude=auto|none|N]\n"
                "  %s in.csv out.csv poly [deg_amp] [deg_ph] [exclude=auto|none|N]\n",
                argv[0], argv[0], argv[0]);
        return 1;
    }
    if (argc >= 4) {
        if (strcmp(argv[3], "poly") == 0) {
            fit.method = LUT_METHOD_POLY;
            if (argc >= 5) {
                fit.deg_amp = atoi(argv[4]);
            }
            if (argc >= 6) {
                fit.deg_ph = atoi(argv[5]);
            }
            if (argc >= 7) {
                fit.exclude = lut_phase0_parse_exclude_arg(argv[6]);
            }
        } else {
            /* ma or numeric legacy */
            fit.method = LUT_METHOD_MA;
            if (strcmp(argv[3], "ma") == 0) {
                if (argc >= 5) {
                    fit.ma_win = atoi(argv[4]);
                }
                if (argc >= 6) {
                    fit.exclude = lut_phase0_parse_exclude_arg(argv[5]);
                }
            } else {
                /* legacy: deg_amp deg_ph exclude → poly */
                fit.method = LUT_METHOD_POLY;
                fit.deg_amp = atoi(argv[3]);
                if (argc >= 5) {
                    fit.deg_ph = atoi(argv[4]);
                }
                if (argc >= 6) {
                    fit.exclude = lut_phase0_parse_exclude_arg(argv[5]);
                }
            }
        }
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
    if (lut_phase0_write_csv(argv[2], &fit) != 0) {
        return 4;
    }
    snprintf(map_path, sizeof(map_path), "%s", argv[2]);
    L = strlen(map_path);
    if (L > 4 && strcmp(map_path + L - 4, ".csv") == 0) {
        memcpy(map_path + L - 4, ".txt", 4);
    } else {
        strncat(map_path, ".txt", sizeof(map_path) - strlen(map_path) - 1);
    }
    lut_phase0_write_map_txt(map_path, &fit, 0);
    printf("[OK] method=%s n=%d exclude=",
           (fit.method == LUT_METHOD_MA) ? "ma" : "poly", fit.n);
    if (fit.exclude == LUT_PHASE0_EXCLUDE_AUTO) {
        printf("auto→");
    } else if (fit.exclude == LUT_PHASE0_EXCLUDE_NONE) {
        printf("none");
    } else {
        printf("manual→");
    }
    for (k = 0; k < fit.n; ++k) {
        if (fit.exclude_mask[k]) {
            printf("%d ", k);
        }
    }
    printf("→ %s\n", argv[2]);
    printf("[OK] map → %s\n", map_path);
    return 0;
}
