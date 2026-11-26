//! Pointwise residuals of the UV-factorized Einstein–scalar equations.
use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

type Field<'py> = [PyReadonlyArray1<'py, f64>; 3];

fn field_slices<'a>(field: &'a Field<'_>) -> PyResult<[&'a [f64]; 3]> {
    let [value, first, second] = field;
    Ok([value.as_slice()?, first.as_slice()?, second.as_slice()?])
}

// Match the grouping of the NumPy sums used by the nonlinear solver.
fn scaled<const N: usize>(terms: [f64; N]) -> f64 {
    terms.iter().sum::<f64>() / (1.0 + terms.iter().map(|term| term.abs()).sum::<f64>())
}

/// Each field triple contains its value and its first two spectral derivatives.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn gubser_nellore_equations<'py>(
    py: Python<'py>,
    x_h_squared: f64,
    uv_power: f64,
    u: PyReadonlyArray1<'py, f64>,
    blackening: Field<'py>,
    warp: Field<'py>,
    scalar: Field<'py>,
    potential_term: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let u = u.as_slice()?;
    let potential = potential_term.as_slice()?;
    let [f, fu, fuu] = field_slices(&blackening)?;
    let [c, cu, cuu] = field_slices(&warp)?;
    let [p, pu, puu] = field_slices(&scalar)?;
    if [f, fu, fuu, c, cu, cuu, p, pu, puu, potential]
        .iter()
        .any(|field| field.len() != u.len())
    {
        return Err(PyValueError::new_err(
            "all fields must match the radial grid",
        ));
    }

    let mut residuals = Array2::zeros((3, u.len()));
    for (i, &r) in u.iter().enumerate() {
        let a_x = 2.0 * r * c[i] + (r * r) * cu[i];
        let phi_x = p[i] + r * pu[i];

        let f1 = r * fuu[i];
        let f2 = (3.0 * x_h_squared * r * a_x + 1.0 - 4.0 / uv_power) * fu[i];
        residuals[[0, i]] = scaled([f1, f2]);

        let w1 = 2.0 * c[i] + 4.0 * r * cu[i] + (r * r) * cuu[i];
        let w2 = (1.0 + 1.0 / uv_power) * (2.0 * c[i] + r * cu[i]);
        let w3 = -x_h_squared * (a_x * a_x);
        let w4 = (phi_x * phi_x) / 6.0;
        residuals[[1, i]] = scaled([w1, w2, w3, w4]);

        let s1 = r * f[i] * (2.0 * pu[i] + r * puu[i]);
        let s2 = (3.0 * x_h_squared * r * f[i] * a_x + (1.0 - 4.0 / uv_power) * f[i] + r * fu[i])
            * phi_x;
        residuals[[2, i]] = scaled([s1, s2, potential[i]]);
    }
    Ok(residuals.into_pyarray(py))
}
