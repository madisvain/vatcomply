//! `f64` stays inside the Python float-token module.

use std::path::Path;

#[test]
fn f64_is_only_used_in_pyfloat() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut hits = Vec::new();
    walk(&root, &mut hits);
    assert!(
        hits.is_empty(),
        "f64 outside pyfloat.rs: {}",
        hits.join(", ")
    );
}

fn walk(dir: &Path, hits: &mut Vec<String>) {
    for entry in std::fs::read_dir(dir).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if path.is_dir() {
            walk(&path, hits);
            continue;
        }
        if path.extension().is_none_or(|ext| ext != "rs") {
            continue;
        }
        if path.file_name().is_some_and(|name| name == "pyfloat.rs") {
            continue;
        }
        let text = std::fs::read_to_string(&path).unwrap();
        if text.contains("f64") {
            hits.push(path.display().to_string());
        }
    }
}
