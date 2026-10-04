#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let text = String::from_utf8_lossy(data);
    let _ = vatcomply::query::last(Some(&text));
    let _ = vatcomply::query::redact(&text);
});
