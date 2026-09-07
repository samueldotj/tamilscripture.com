//! FNV-1a 64-bit, used for the content build id. Not cryptographic; it only
//! needs to change whenever any input byte changes.

pub struct Fnv64(u64);

impl Fnv64 {
    pub fn new() -> Self {
        Fnv64(0xcbf29ce484222325)
    }

    pub fn update(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 ^= b as u64;
            self.0 = self.0.wrapping_mul(0x100000001b3);
        }
    }

    pub fn finish(&self) -> u64 {
        self.0
    }
}
