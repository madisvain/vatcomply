#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    vatcomply::vies::parse_vies_response(data);
});
