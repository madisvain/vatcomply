use mimalloc::MiMalloc;

#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;

fn main() {
    let code = match vatcomply::run() {
        Ok(code) => code,
        Err(error) => {
            eprintln!("vatcomply: {error}");
            1
        }
    };
    std::process::exit(code);
}
