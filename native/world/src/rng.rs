//! A world's random, as Python's `random.Random` draws it (the Mersenne Twister, MT19937): the same seed, the same
//! state, the same numbers, so a log made by the Python engine replays on this one (PLAN_WORLD_ENGINE.md).
//! What a world draws: `random()`, `randint(a, b)` and `randrange(n)`; a state goes in and out as Python's
//! `getstate()` gives it (624 words and the index).

const N: usize = 624;
const M: usize = 397;

#[derive(Clone)]
pub struct Rng {
    mt: [u32; N],
    index: usize,
}

impl Rng {
    /// `random.Random(seed)` of a whole number not below zero (a world's is 0).
    pub fn seeded(seed: u64) -> Rng {
        let mut key = vec![(seed & 0xffff_ffff) as u32];
        if seed >> 32 != 0 {
            key.push((seed >> 32) as u32);
        }
        let mut rng = Rng {
            mt: [0; N],
            index: N,
        };
        rng.init_by_array(&key);
        rng
    }

    /// Python's `getstate()[1]`: the 624 words and the index.
    pub fn from_state(words: &[u32], index: usize) -> Option<Rng> {
        if words.len() != N || index > N {
            return None;
        }
        let mut mt = [0; N];
        mt.copy_from_slice(words);
        Some(Rng { mt, index })
    }

    pub fn state(&self) -> (Vec<u32>, usize) {
        (self.mt.to_vec(), self.index)
    }

    fn init_genrand(&mut self, s: u32) {
        self.mt[0] = s;
        for i in 1..N {
            self.mt[i] = 1_812_433_253u32
                .wrapping_mul(self.mt[i - 1] ^ (self.mt[i - 1] >> 30))
                .wrapping_add(i as u32);
        }
        self.index = N;
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.init_genrand(19_650_218);
        let (mut i, mut j) = (1usize, 0usize);
        for _ in 0..N.max(key.len()) {
            self.mt[i] = (self.mt[i]
                ^ (self.mt[i - 1] ^ (self.mt[i - 1] >> 30)).wrapping_mul(1_664_525))
            .wrapping_add(key[j])
            .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
        }
        for _ in 0..N - 1 {
            self.mt[i] = (self.mt[i]
                ^ (self.mt[i - 1] ^ (self.mt[i - 1] >> 30)).wrapping_mul(1_566_083_941))
            .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
        }
        self.mt[0] = 0x8000_0000;
        self.index = N;
    }

    fn next_u32(&mut self) -> u32 {
        if self.index >= N {
            for k in 0..N {
                let y = (self.mt[k] & 0x8000_0000) | (self.mt[(k + 1) % N] & 0x7fff_ffff);
                let mut v = self.mt[(k + M) % N] ^ (y >> 1);
                if y & 1 != 0 {
                    v ^= 0x9908_b0df;
                }
                self.mt[k] = v;
            }
            self.index = 0;
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        y
    }

    /// `random()`: 53 bits, in [0, 1).
    pub fn random(&mut self) -> f64 {
        let a = (self.next_u32() >> 5) as f64;
        let b = (self.next_u32() >> 6) as f64;
        (a * 67_108_864.0 + b) * (1.0 / 9_007_199_254_740_992.0)
    }

    /// `getrandbits(k)`, k of 1 to 64.
    fn getrandbits(&mut self, k: u32) -> u64 {
        if k <= 32 {
            return (self.next_u32() >> (32 - k)) as u64;
        }
        let low = self.next_u32() as u64;
        let high = (self.next_u32() >> (64 - k)) as u64;
        low | (high << 32)
    }

    /// `_randbelow(n)`: a whole number in [0, n), n above 0, drawn as Python draws it (whole words, refused
    /// above n).
    fn below(&mut self, n: u64) -> u64 {
        let k = 64 - n.leading_zeros();
        let mut r = self.getrandbits(k);
        while r >= n {
            r = self.getrandbits(k);
        }
        r
    }

    /// `randrange(n)`: None for an empty range (Python's ValueError).
    pub fn randrange(&mut self, n: i64) -> Option<i64> {
        if n <= 0 {
            return None;
        }
        Some(self.below(n as u64) as i64)
    }

    /// `randint(a, b)`, both included: None when a is above b.
    pub fn randint(&mut self, a: i64, b: i64) -> Option<i64> {
        let width = (b as i128) - (a as i128) + 1;
        if width <= 0 || width > u64::MAX as i128 {
            return None;
        }
        Some((a as i128 + self.below(width as u64) as i128) as i64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_first_draws_of_seed_zero_are_pythons() {
        // random.Random(0): .random() twice, then .randint(1, 6) and .randrange(10)
        let mut r = Rng::seeded(0);
        assert_eq!(r.random(), 0.8444218515250481);
        assert_eq!(r.random(), 0.7579544029403025);
        assert_eq!(r.randint(1, 6), Some(4));
        assert_eq!(r.randrange(10), Some(0));
    }
}
