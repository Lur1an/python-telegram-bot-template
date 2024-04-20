use pyo3::prelude::*;

/// This function adds two unsigned 64-bit integers.
#[pyfunction]
#[pyo3(signature = (a, b=0, /))]
fn add(a: u64, b: u64) -> u64 {
    a + b
}

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: f64, b: usize) -> PyResult<String> {
    Ok((a + b as f64).to_string())
}

/// A Python module implemented in Rust.
#[pymodule]
fn rustlib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}
