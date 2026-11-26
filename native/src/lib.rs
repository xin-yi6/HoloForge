//! Optional numerical kernels for HoloForge.
mod gubser_nellore;
use ivp::prelude::{FirstOrderSystem, Ivp, Method};
use ivp::status::Status;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

struct HardWall {
    mass_squared: f64,
}

impl FirstOrderSystem for HardWall {
    fn derivative(&self, x: f64, state: &[f64], derivative: &mut [f64]) {
        derivative[0] = state[1];
        derivative[1] = state[1] / x - self.mass_squared * state[0];
    }
}

/// Return V'(1) for V(epsilon)=0, V'(epsilon)=1 and dimensionless mass m*z_m.
#[pyfunction]
fn hard_wall_residual(
    py: Python<'_>,
    mass: f64,
    epsilon: f64,
    rtol: f64,
    atol: f64,
) -> PyResult<f64> {
    let mass_squared = mass * mass;
    if !mass_squared.is_finite()
        || !(0.0 < epsilon && epsilon < 1.0)
        || !rtol.is_finite()
        || rtol <= 0.0
        || !atol.is_finite()
        || atol <= 0.0
    {
        return Err(PyValueError::new_err(
            "expected finite mass squared, 0 < epsilon < 1, and finite positive tolerances",
        ));
    }
    py.detach(|| {
        let equation = HardWall { mass_squared };
        let solution = Ivp::first_order(&equation, epsilon, 1.0, &[0.0, 1.0])
            .method(Method::DOP853)
            .rtol(rtol.max(100.0 * f64::EPSILON))
            .atol(atol)
            .dense_output(false)
            .solve()
            .map_err(|e| {
                PyRuntimeError::new_err(format!("Rust hard-wall integration failed: {e}"))
            })?;
        if solution.status != Status::Success {
            return Err(PyRuntimeError::new_err(format!(
                "Rust hard-wall integration failed: {:?}",
                solution.status
            )));
        }
        match (solution.t.last(), solution.y.last()) {
            (Some(x), Some(state))
                if (*x - 1.0).abs() <= 2.0 * f64::EPSILON && state[1].is_finite() =>
            {
                Ok(state[1])
            }
            _ => Err(PyRuntimeError::new_err(
                "Rust hard-wall integration did not produce a finite IR derivative",
            )),
        }
    })
}

#[pymodule]
fn holoforge_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_function(wrap_pyfunction!(hard_wall_residual, module)?)?;
    module.add_function(wrap_pyfunction!(
        gubser_nellore::gubser_nellore_equations,
        module
    )?)?;
    Ok(())
}
