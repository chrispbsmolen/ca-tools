#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
SEXP C_maxclique_disjoint(SEXP, SEXP, SEXP, SEXP, SEXP);
SEXP C_count_core(SEXP, SEXP, SEXP, SEXP);
SEXP C_flexpos(SEXP, SEXP, SEXP, SEXP);
SEXP C_markflex_pin(SEXP, SEXP, SEXP);
static const R_CallMethodDef callMethods[] = {
    {"C_maxclique_disjoint", (DL_FUNC) &C_maxclique_disjoint, 5},
    {"C_count_core", (DL_FUNC) &C_count_core, 4},
    {"C_flexpos", (DL_FUNC) &C_flexpos, 4},
    {"C_markflex_pin", (DL_FUNC) &C_markflex_pin, 3},
    {NULL, NULL, 0}
};
void R_init_cafast(DllInfo *dll) {
    R_registerRoutines(dll, NULL, callMethods, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
}
