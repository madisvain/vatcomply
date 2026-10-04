#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    let _ = vatcomply::rates::parse::parse_ecb_xml(data);
});
